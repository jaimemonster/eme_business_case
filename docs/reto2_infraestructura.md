# Reto 2 · Infraestructura del servicio

Cómo está montada la parte de Google Cloud que ejecuta y publica la propuesta de
reposición: qué existe, por qué está así, cómo se reproduce desde cero y qué
hacer cuando algo falla.

> Este documento es **operativo**, no es un entregable. El esquema conceptual de
> producción vive en [`reto2_arquitectura_produccion.md`](reto2_arquitectura_produccion.md)
> y en el propio servicio.

---

## 1. Qué hay montado

| Pieza | Valor | Para qué |
|-------|-------|----------|
| Cuenta de Google | `jmdm.contact@gmail.com` | Propietaria del proyecto |
| Organización | `jmdm-contact-org` (ID `82869294278`) | El proyecto cuelga de ella; impone políticas de seguridad |
| Proyecto | `eme-reposicion` (nº `761842722633`) | Todo vive aquí |
| Facturación | `0150E8-D3B901-C62C1D` | Crédito de prueba, vence el 16/02/2027 |
| Región | `europe-southwest1` (Madrid) | Latencia y residencia del dato |
| Cuenta de servicio | `reposicion-bot@eme-reposicion.iam.gserviceaccount.com` | La identidad con la que corre el servicio y escribe el Sheet |
| Google Sheet | `16mATc295JLdg6XusheIa55NpjOHVUisGniq6ihc4FFk` | El entregable que revisa Compras |
| Servicio | `https://eme-reposicion-761842722633.europe-southwest1.run.app` | La web y el trabajo que dispara el reloj |
| Reloj | Cloud Scheduler `reposicion-diaria`, en `europe-west1` | Diario a las 00:00 `Europe/Madrid` |

Estos valores están en [`src/config.py`](../src/config.py) y se pueden sobrescribir
por variables de entorno (`EME_PROYECTO_GCP`, `EME_REGION_GCP`,
`EME_CUENTA_SERVICIO`, `EME_SHEET_ID`), para que el servicio desplegado no dependa
de valores escritos a mano en el código.

### APIs activadas

| API | Para qué |
|-----|----------|
| `run.googleapis.com` | Ejecutar el servicio |
| `cloudbuild.googleapis.com` | Construir la imagen a partir del código |
| `artifactregistry.googleapis.com` | Guardar la imagen construida |
| `cloudscheduler.googleapis.com` | El reloj que lanza el cálculo cada día |
| `sheets.googleapis.com` | Escribir la propuesta |
| `drive.googleapis.com` | Crear y compartir el fichero del Sheet |

---

## 2. La decisión importante: sin claves descargadas

**No existe ningún fichero de credenciales en ninguna parte, y es deliberado.**

La organización tiene activada la política `iam.disableServiceAccountKeyCreation`,
que prohíbe descargar claves JSON de cuentas de servicio. Google la activa por
defecto en las organizaciones nuevas, y hace bien: una clave descargada es un
fichero que se puede filtrar, que no caduca y que funciona desde cualquier sitio.

En lugar de levantar la política, se usan los dos mecanismos correctos:

- **En Cloud Run**: el servicio se despliega *como* la cuenta de servicio
  (`--service-account`). Dentro del contenedor, las credenciales se piden a Google
  en cada arranque y caducan en una hora. No hay nada que guardar.
- **En local**: el usuario tiene el rol `roles/iam.serviceAccountTokenCreator`
  sobre la cuenta de servicio, lo que le permite **generar credenciales temporales
  del robot** sin poseer ninguna clave suya.

El efecto secundario es bueno: el Sheet se escribe siempre con la misma identidad,
corra el código donde corra, así que lo que se prueba en local es lo que pasa en
producción.

---

## 3. Reproducirlo desde cero

Si hubiera que montarlo otra vez, en otra cuenta:

```bash
# --- 1 · herramientas y sesión ---
brew install --cask google-cloud-sdk
gcloud auth login
gcloud auth application-default login      # SIN --scopes: ver problema C

# --- 2 · proyecto y facturación ---
gcloud projects create eme-reposicion                 # o reutilizar uno existente
gcloud config set project eme-reposicion
gcloud billing accounts list
gcloud billing projects link eme-reposicion --billing-account=TU_ACCOUNT_ID

# --- 3 · APIs ---
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com sheets.googleapis.com drive.googleapis.com

# --- 4 · identidad del servicio ---
gcloud iam service-accounts create reposicion-bot \
  --display-name "Robot de reposicion"

gcloud iam service-accounts add-iam-policy-binding \
  reposicion-bot@eme-reposicion.iam.gserviceaccount.com \
  --member="user:TU_CORREO" \
  --role="roles/iam.serviceAccountTokenCreator"
```

Y después, **a mano**: crear el Google Sheet y compartirlo como **editor** con
`reposicion-bot@eme-reposicion.iam.gserviceaccount.com`. Sin este paso el robot
no puede escribir aunque tenga todos los permisos de Google Cloud: son dos
sistemas de permisos distintos y hay que atender a los dos.

---

## 4. Comprobar que todo está bien

```bash
gcloud config list                                   # cuenta y proyecto activos
gcloud billing projects describe eme-reposicion      # billingEnabled: true
gcloud services list --enabled                       # las seis APIs
gcloud iam service-accounts list                     # existe reposicion-bot

# la prueba de fuego: generar credenciales del robot sin tener su clave
gcloud auth print-access-token \
  --impersonate-service-account=reposicion-bot@eme-reposicion.iam.gserviceaccount.com
```

Si el último comando devuelve un token, la cadena completa funciona.

---

## 5. Problemas que ya nos han pasado

### A · «No veo los proyectos en la consola, pero `gcloud projects list` sí los muestra»

El selector de recursos de la consola estaba filtrado por la organización, y los
proyectos recién creados no colgaban de ella. **No es un fallo**: hay que abrir el
desplegable de organización y cambiar a *Sin organización*, o quitar el filtro.

Para ver de qué cuelga cada proyecto:

```bash
gcloud projects list --format="table(projectId,name,parent.type,parent.id)"
```

### B · `FAILED_PRECONDITION: Key creation is not allowed on this service account`

Es la política `iam.disableServiceAccountKeyCreation` haciendo su trabajo.
**La solución no es desactivarla**, sino no necesitar la clave: ver el apartado 2.

Se *podría* levantar con
`gcloud resource-manager org-policies disable-enforce iam.disableServiceAccountKeyCreation --project=eme-reposicion`,
pero sería cambiar una buena práctica por comodidad. No se ha hecho.

### C · «Google ha bloqueado el acceso» al ejecutar `gcloud auth application-default login`

Pasa al añadir `--scopes` con permisos de Sheets y Drive: la organización rechaza
que el cliente OAuth de `gcloud` pida esos permisos para un usuario.

**Solución**: hacer el login normal, sin `--scopes`, y obtener los permisos de
Sheets por impersonación de la cuenta de servicio (apartado 2). Es además la
forma correcta.

### D · `PERMISSION_DENIED` al impersonar, con el rol ya concedido

Propagación de IAM. Tarda entre unos segundos y un par de minutos. Reintentar
antes de tocar nada; en nuestro caso propagó en diez segundos.

### E · `does not have storage.objects.get access` al desplegar

Cloud Build construye la imagen usando la **cuenta de servicio por defecto de
Compute** (`<número-de-proyecto>-compute@developer.gserviceaccount.com`), y en los
proyectos nuevos esa cuenta ya no trae permisos de serie. Se le conceden:

```bash
SA="761842722633-compute@developer.gserviceaccount.com"
for ROL in roles/cloudbuild.builds.builder roles/storage.objectAdmin \
           roles/artifactregistry.writer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding eme-reposicion \
    --member="serviceAccount:$SA" --role="$ROL" --condition=None
done
```

### F · El contenedor arranca pero la web da 500: `window shape cannot be larger…`

Versiones. El entorno local corre Python 3.9 y el contenedor 3.11, así que `pip`
resolvía versiones distintas de numpy y scikit-learn, y la combinación del
contenedor rompía al entrenar el modelo. **El error no se reproducía en local**,
que es lo que lo hace molesto.

Solución: fijar las versiones en `requirements.txt`. Un build reproducible vale
más que estar al día, y en un despliegue con fecha de entrega, mucho más.

---

## 6. Despliegue

Desplegado y funcionando. Los comandos reales son éstos:

```bash
# el servicio, construido desde el código fuente
gcloud run deploy eme-reposicion \
  --source . \
  --region europe-southwest1 \
  --service-account reposicion-bot@eme-reposicion.iam.gserviceaccount.com \
  --allow-unauthenticated

# el reloj, que entiende la zona horaria de Madrid sin traducir a UTC
gcloud scheduler jobs create http reposicion-diaria \
  --location europe-west1 \
  --schedule "0 0 * * *" \
  --time-zone "Europe/Madrid" \
  --uri "https://eme-reposicion-761842722633.europe-southwest1.run.app/jobs/reposicion" \
  --http-method POST \
  --headers "x-eme-token=EL_TOKEN" \
  --max-retry-attempts 3 --min-backoff 30s --attempt-deadline 300s
```

**Cloud Scheduler no existe en `europe-southwest1`** (Madrid), de ahí que el reloj
viva en `europe-west1` aunque el servicio esté en Madrid. La región del reloj no
afecta a la hora: el disparo se programa con `--time-zone "Europe/Madrid"`.

El servicio se despliega con `--set-env-vars EME_TOKEN_TRABAJO=…`, un secreto
compartido con el reloj. La web es pública, así que sin esa comprobación
cualquiera que diera con la URL podría lanzar el cálculo.

La web va a ser pública (`--allow-unauthenticated`) para que se pueda abrir sin
cuenta de Google. Eso deja también expuesta la dirección que dispara el cálculo,
así que **`/jobs/reposicion` comprueba la identidad de quien llama** y solo acepta
la petición si viene firmada por el Scheduler.

---

## 7. Despliegue continuo (escrito, sin activar)

`.github/workflows/desplegar.yml` construye y despliega el servicio cuando cambia
el código. **Está desactivado a propósito**: solo se puede lanzar a mano desde la
pestaña Actions de GitHub, porque el proveedor de identidad todavía no existe y un
disparo automático fallaría en el primer merge a `main`.

Hoy el despliegue se hace con un comando (apartado 6). Esto es el siguiente paso,
no el actual.

### Por qué Workload Identity y no una clave

La misma razón del apartado 2: la organización prohíbe descargar claves de cuenta
de servicio, y hace bien. Workload Identity permite que GitHub Actions se
identifique ante Google **sin que exista ningún secreto descargable**: Google
confía en los tokens que firma GitHub para ese repositorio concreto.

### Para activarlo

```bash
PROYECTO=eme-reposicion
NUMERO=761842722633
REPO=jaimemonster/eme_business_case      # ajústalo al nombre real del repositorio

gcloud iam workload-identity-pools create github \
  --location=global --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github \
  --location=global --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${REPO}'"

# Permitir que SOLO ese repositorio actúe como la cuenta de servicio
gcloud iam service-accounts add-iam-policy-binding \
  reposicion-bot@${PROYECTO}.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${NUMERO}/locations/global/workloadIdentityPools/github/attribute.repository/${REPO}"
```

La condición `attribute-condition` es lo que impide que otro repositorio de GitHub
pueda usar esta identidad. Sin ella, cualquiera que supiera el número del proyecto
podría desplegar.

Después, descomentar el disparo por `push` en el workflow.
