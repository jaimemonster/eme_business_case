"""Banco de pruebas: mete modelos de verdad en el mismo backtesting."""
import sys, warnings, time
sys.path.insert(0, '/Users/jaimemartinezdemiguel/Documents/Projects/eme_business_case')
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from src import demand as d
from src.clean import ejecutar_limpieza

H = 14
t = ejecutar_limpieza(persistir=False)
serie = d._con_grupo(d.serie_demanda(t["ventas"], t["producto"], t.get("stock_semanal")), t["producto"])

def _entrena(hist, horizonte, constructor, cortes=40):
    """Mismo armazón que entrenar_modelo_nivel, con el estimador que le pases."""
    semanas = np.sort(hist["inicio_semana"].unique())
    cal = min(26, max(8, len(semanas) // 3))
    cand = semanas[cal:-horizonte] if len(semanas) > cal + horizonte else []
    if len(cand) < 5: return None
    cand = cand[-cortes:]
    X = []
    real = hist.set_index(["grupo", "inicio_semana"])["unidades"]
    for c in cand:
        c = pd.Timestamp(c)
        r = d._rasgos_ml(hist[hist["inicio_semana"] <= c], c, horizonte)
        r["objetivo"] = [real.get((g, w), np.nan) for g, w in zip(r["grupo"], r["inicio_semana"])]
        X.append(r.dropna(subset=["objetivo"]))
    datos = pd.concat(X, ignore_index=True)
    y = datos["objetivo"]
    cols = [c for c in datos.columns if c not in ("objetivo", "inicio_semana")]
    datos = datos[cols].copy()
    m = constructor()
    if getattr(m, "_necesita_dummies", False) or not hasattr(m, "categorical_features"):
        Xd = pd.get_dummies(datos, columns=["grupo"]).fillna(0.0)
        m.fit(Xd, y); return m, list(Xd.columns), True
    datos["grupo"] = datos["grupo"].astype("category")
    m.fit(datos, y); return m, cols, False

def _predice(hist, corte, horizonte, entrenado):
    m, cols, dummies = entrenado
    r = d._rasgos_ml(hist, corte, horizonte)
    if dummies:
        X = pd.get_dummies(r[[c for c in cols if not c.startswith("grupo_")] + ["grupo"]]
                           if "grupo" in r else r, columns=["grupo"]).fillna(0.0)
        X = X.reindex(columns=cols, fill_value=0.0)
    else:
        X = r[cols].copy(); X["grupo"] = X["grupo"].astype("category")
    r["p"] = np.clip(m.predict(X), 0, None)
    return r.groupby("grupo")["p"].sum()

def metodo_ml(constructor):
    cache = {}
    def fn(hist, corte, horizonte, modelo_entrenado=None):
        k = (len(hist), horizonte)
        if k not in cache:
            cache[k] = _entrena(hist, horizonte, constructor)
        if cache[k] is None: return d.nivel_estacional(hist, corte, horizonte)
        return _predice(hist, corte, horizonte, cache[k])
    return fn

from sklearn.ensemble import (HistGradientBoostingRegressor as HGB, RandomForestRegressor as RF,
                              ExtraTreesRegressor as ET, GradientBoostingRegressor as GB)
from sklearn.linear_model import Ridge, PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def ridge():
    p = make_pipeline(StandardScaler(), Ridge(alpha=5.0)); p._necesita_dummies = True; return p
def poisson():
    p = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-3, max_iter=500)); p._necesita_dummies = True; return p
def rf():
    m = RF(n_estimators=300, min_samples_leaf=5, random_state=42, n_jobs=-1); m._necesita_dummies = True; return m
def et():
    m = ET(n_estimators=300, min_samples_leaf=5, random_state=42, n_jobs=-1); m._necesita_dummies = True; return m
def gb_sk():
    m = GB(n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42); m._necesita_dummies = True; return m

CANDIDATOS = {
    "hgb_actual":  lambda: HGB(max_depth=4, max_iter=250, learning_rate=0.06, min_samples_leaf=25,
                               l2_regularization=1.0, categorical_features=["grupo"], random_state=42),
    "hgb_poisson": lambda: HGB(loss="poisson", max_depth=4, max_iter=250, learning_rate=0.06,
                               min_samples_leaf=25, l2_regularization=1.0,
                               categorical_features=["grupo"], random_state=42),
    "hgb_hondo":   lambda: HGB(max_depth=8, max_iter=600, learning_rate=0.05, min_samples_leaf=10,
                               categorical_features=["grupo"], random_state=42),
    "hgb_llano":   lambda: HGB(max_depth=2, max_iter=400, learning_rate=0.05, min_samples_leaf=40,
                               l2_regularization=3.0, categorical_features=["grupo"], random_state=42),
    "ridge":       ridge,
    "poisson_lin": poisson,
    "random_forest": rf,
    "extra_trees": et,
    "gb_clasico":  gb_sk,
}
for nombre, c in CANDIDATOS.items():
    d.METODOS_NIVEL[nombre] = metodo_ml(c)

metodos = ("plano", "estacional", "ano_anterior") + tuple(CANDIDATOS)
t0 = time.time()
comp = d.comparar_metodos(serie, H, n_cortes=12, metodos=metodos, paso=4)
print(comp.to_string(index=False))
print(f"\n{time.time()-t0:.0f} s")
comp.to_csv('/tmp/bench.csv', index=False)
