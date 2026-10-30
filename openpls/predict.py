"""Évaluation de la capacité prédictive hors échantillon.

PLSpredict (Shmueli et al. 2016, 2019) : validation croisée à k plis répétée.
Sur chaque pli, le modèle est estimé sur les données d'apprentissage ; pour les
observations mises de côté, on calcule les scores des latentes exogènes avec les poids
d'apprentissage, on prédit les latentes endogènes par le modèle structurel, puis leurs
indicateurs via les chargements. Comparaisons :
  * Q²_predict = 1 - SCE(PLS) / SCE(moyenne d'apprentissage)  (> 0 : mieux que la moyenne)
  * RMSE et MAE de PLS vs un modèle linéaire (LM) qui régresse chaque indicateur endogène
    sur tous les indicateurs exogènes. PLS « bat » LM si son erreur est plus faible.

CVPAT (Liengaard et al. 2021 ; Sharma et al. 2023) : test t apparié sur les pertes
quadratiques moyennes par observation, PLS contre la moyenne des indicateurs (IA)
et contre LM. Différence de perte négative et significative = PLS prédit mieux.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .model import Model


def _exogenous(model: Model) -> list[int]:
    return [j for j in range(len(model.latents)) if not model.path[:, j].any()]


def _fold_predictions(train: pd.DataFrame, test: pd.DataFrame, model: Model, approach: str, **fit_kwargs):
    from .algorithm import fit
    from .effects import total_effects

    res = fit(train, model, **fit_kwargs)
    lvs = model.latents
    exo = _exogenous(model)
    endo = model.endogenous()
    mu, sd = train[model.indicators].mean(), train[model.indicators].std(ddof=1)
    z_test = (test[model.indicators] - mu) / sd

    # scores hors échantillon avec les poids d'apprentissage (déjà normalisés sur l'apprentissage)
    scores = pd.DataFrame(index=test.index, columns=lvs, dtype=float)
    for lv in lvs:
        w = res.outer_weights[lv]
        scores[lv] = z_test[list(w.index)].to_numpy() @ w.to_numpy()

    b = res.path_coefficients
    pred_lv = pd.DataFrame(index=test.index, columns=[lvs[j] for j in endo], dtype=float)
    if approach == "EA":  # antécédents les plus lointains : uniquement les exogènes
        t = total_effects(res)
        ex_names = [lvs[j] for j in exo]
        for j in endo:
            pred_lv[lvs[j]] = scores[ex_names].to_numpy() @ t.loc[ex_names, lvs[j]].to_numpy()
    elif approach == "DA":  # antécédents directs (scores observés des prédécesseurs)
        for j in endo:
            pred = [lvs[i] for i in model.predecessors(j)]
            pred_lv[lvs[j]] = scores[pred].to_numpy() @ b.loc[pred, lvs[j]].to_numpy()
    else:
        raise ValueError("approach doit valoir 'EA' ou 'DA'")

    endo_inds, pls_pred = [], {}
    for j in endo:
        lv = lvs[j]
        for ind in model.measurement[lv]:
            endo_inds.append(ind)
            lam = res.outer_loadings[(lv, ind)]
            pls_pred[ind] = pred_lv[lv].to_numpy() * lam * sd[ind] + mu[ind]
    pls_pred = pd.DataFrame(pls_pred, index=test.index)

    exo_inds = [ind for j in exo for ind in model.measurement[lvs[j]]]
    xtr = np.column_stack([np.ones(len(train)), train[exo_inds].to_numpy(float)])
    xte = np.column_stack([np.ones(len(test)), test[exo_inds].to_numpy(float)])
    beta = np.linalg.lstsq(xtr, train[endo_inds].to_numpy(float), rcond=None)[0]
    lm_pred = pd.DataFrame(xte @ beta, index=test.index, columns=endo_inds)
    naive = pd.DataFrame(np.tile(train[endo_inds].mean().to_numpy(), (len(test), 1)),
                         index=test.index, columns=endo_inds)
    # latentes : score « observé » hors échantillon vs prédiction ; benchmark = 0 (moyenne)
    actual_lv = scores[pred_lv.columns]
    return pls_pred, lm_pred, naive, pred_lv, actual_lv


def _cv_predictions(data, model, k, repetitions, seed, approach, **fit_kwargs):
    if model.interactions:
        raise ValueError("PLSpredict n'est pas disponible pour les modèles avec interaction")
    if model.higher_order:
        raise ValueError("PLSpredict n'est pas disponible pour les modèles d'ordre supérieur")
    if not model.endogenous():
        raise ValueError("Le modèle n'a pas de variable latente endogène")
    n = len(data)
    if k < 2 or k > n:
        raise ValueError("Nombre de plis invalide")
    rng = np.random.default_rng(seed)
    data = data.reset_index(drop=True)
    reps = []
    for _ in range(repetitions):
        folds = np.array_split(rng.permutation(n), k)
        parts = [[], [], [], [], []]
        for f in folds:
            test = data.iloc[f]
            train = data.drop(index=f)
            for acc, out in zip(parts, _fold_predictions(train, test, model, approach, **fit_kwargs)):
                acc.append(out)
        reps.append([pd.concat(p).sort_index() for p in parts])
    return data, reps


def pls_predict(data: pd.DataFrame, model: Model, k: int = 10, repetitions: int = 10, seed: int | None = 42,
                approach: str = "EA", **fit_kwargs) -> dict[str, pd.DataFrame]:
    """Retourne {"indicators": tableau par indicateur endogène, "latents": Q²_predict par latente}."""
    data, reps = _cv_predictions(data, model, k, repetitions, seed, approach, **fit_kwargs)
    rows = {}
    for pls, lm, naive, _, _ in reps:
        actual = data[pls.columns]
        for ind in pls.columns:
            e_pls, e_lm, e_nv = (actual[ind] - pls[ind]), (actual[ind] - lm[ind]), (actual[ind] - naive[ind])
            r = rows.setdefault(ind, [])
            r.append({
                "Q2_predict": 1 - (e_pls**2).sum() / (e_nv**2).sum(),
                "PLS_RMSE": np.sqrt((e_pls**2).mean()), "PLS_MAE": e_pls.abs().mean(),
                "LM_RMSE": np.sqrt((e_lm**2).mean()), "LM_MAE": e_lm.abs().mean(),
            })
    ind_tbl = pd.DataFrame({ind: pd.DataFrame(r).mean() for ind, r in rows.items()}).T
    ind_tbl["PLS < LM (RMSE)"] = ind_tbl["PLS_RMSE"] < ind_tbl["LM_RMSE"]

    lv_rows = {}
    for _, _, _, pred_lv, actual_lv in reps:
        for lv in pred_lv.columns:
            e = actual_lv[lv] - pred_lv[lv]
            lv_rows.setdefault(lv, []).append({
                "Q2_predict": 1 - (e**2).sum() / ((actual_lv[lv] - actual_lv[lv].mean()) ** 2).sum(),
                "RMSE": np.sqrt((e**2).mean()), "MAE": e.abs().mean(),
            })
    lv_tbl = pd.DataFrame({lv: pd.DataFrame(r).mean() for lv, r in lv_rows.items()}).T
    return {"indicators": ind_tbl, "latents": lv_tbl}


def cvpat(data: pd.DataFrame, model: Model, k: int = 10, repetitions: int = 10, seed: int | None = 42,
          approach: str = "EA", **fit_kwargs) -> pd.DataFrame:
    """CVPAT : PLS contre IA (moyenne des indicateurs) et contre LM, par latente endogène et global.

    perte = moyenne (sur les indicateurs, standardisés par l'écart-type de l'échantillon)
    des erreurs quadratiques ; moyennée sur les répétitions pour chaque observation.
    H1 unilatérale : la perte de PLS est plus faible que celle du benchmark."""
    data, reps = _cv_predictions(data, model, k, repetitions, seed, approach, **fit_kwargs)
    endo_lvs = [model.latents[j] for j in model.endogenous()]
    scale = data[model.indicators].std(ddof=1)

    def losses(i):
        out = {}
        for lv in endo_lvs + ["Global"]:
            inds = [c for c in reps[0][0].columns if lv == "Global" or c in model.measurement[lv]]
            acc = []
            for rep in reps:
                actual = data[inds]
                acc.append((((actual - rep[i][inds]) / scale[inds]) ** 2).mean(axis=1).to_numpy())
            out[lv] = np.mean(acc, axis=0)
        return out

    pls_l, lm_l, ia_l = losses(0), losses(1), losses(2)
    rows = []
    for bench, bl in (("IA", ia_l), ("LM", lm_l)):
        for lv in endo_lvs + ["Global"]:
            d = pls_l[lv] - bl[lv]
            se = d.std(ddof=1) / np.sqrt(len(d))
            t = d.mean() / se if se > 0 else np.nan
            rows.append({"benchmark": bench, "latente": lv, "perte_PLS": pls_l[lv].mean(),
                         "perte_benchmark": bl[lv].mean(), "diff_perte": d.mean(), "t_value": t,
                         "p_value": stats.t.cdf(t, df=len(d) - 1) if np.isfinite(t) else np.nan})
    out = pd.DataFrame(rows).set_index(["benchmark", "latente"])
    out["PLS meilleur (p<0,05)"] = (out["diff_perte"] < 0) & (out["p_value"] < 0.05)
    return out
