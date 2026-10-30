"""Évaluation de l'endogénéité par copules gaussiennes (Park & Gupta 2012 ;
Hult et al. 2018 ; Becker, Proksch & Ringle 2022).

Pour une latente endogène Y et ses prédécesseurs X_1..X_p (scores PLS), on ajoute à la
régression de Y un terme de copule C_k = Φ⁻¹(F̂(X_k)) pour un ou plusieurs prédécesseurs
(F̂ = fonction de répartition empirique, rang/(n+1)). Un terme de copule significatif signale
que X_k est corrélé à l'erreur (endogénéité) ; le coefficient de X_k dans ce modèle est
alors une estimation corrigée.

Conditions : le régresseur testé doit être non normal (sinon la copule n'est pas
identifiée) — le test de Shapiro-Wilk est rapporté, et la conclusion est déclarée
« non interprétable » quand un régresseur du modèle de copule n'est pas significativement non normal. L'inférence se fait par bootstrap
de la régression sur les scores, comme dans Hult et al. (2018).
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats


def copula_term(v: np.ndarray) -> np.ndarray:
    r = stats.rankdata(v)
    return stats.norm.ppf(r / (len(v) + 1))


def _ols(y, x):
    return np.linalg.lstsq(x, y, rcond=None)[0]


def copula_regression(scores: pd.DataFrame, target: str, predictors: list[str], copulas: list[str],
                      n_boot: int = 1000, seed: int | None = 42) -> pd.DataFrame:
    n = len(scores)
    y = scores[target].to_numpy()
    cols = predictors + [f"copule({c})" for c in copulas]
    base = np.column_stack([scores[predictors].to_numpy()] + [copula_term(scores[c].to_numpy()) for c in copulas])
    design = np.column_stack([np.ones(n), base])
    est = _ols(y, design)[1:]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        sub = scores.iloc[i]
        xb = np.column_stack([sub[predictors].to_numpy()] + [copula_term(sub[c].to_numpy()) for c in copulas])
        draws.append(_ols(sub[target].to_numpy(), np.column_stack([np.ones(n), xb]))[1:])
    draws = np.array(draws)
    se = draws.std(axis=0, ddof=1)
    t = est / se
    p = 2 * stats.t.sf(np.abs(t), df=n_boot - 1)
    return pd.DataFrame({"coefficient": est, "std_error": se, "t_value": t, "p_value": p}, index=cols)


def gaussian_copula(res, target: str, n_boot: int = 1000, seed: int | None = 42, max_combination: int = 3) -> dict:
    """Teste toutes les combinaisons de termes de copule (jusqu'à `max_combination`) pour `target`.

    Retourne {"normality": Shapiro-Wilk des prédécesseurs, "models": tableau long des estimations,
    "summary": une ligne par copule et par modèle}."""
    model = res.model
    if target not in model.latents:
        raise KeyError(f"Latente inconnue : {target}")
    j = model.latents.index(target)
    preds = [model.latents[i] for i in model.predecessors(j)]
    if not preds:
        raise ValueError(f"{target} n'a aucun prédécesseur")
    sc = res.scores
    norm_rows = {}
    for p in preds:
        stat, pv = stats.shapiro(sc[p].to_numpy()[:5000])
        norm_rows[p] = {"Shapiro-Wilk W": stat, "p_value": pv, "non normal (p<0,05)": pv < 0.05}
    normality = pd.DataFrame.from_dict(norm_rows, orient="index")

    tables, summary = [], []
    for size in range(1, min(len(preds), max_combination) + 1):
        for combo in combinations(preds, size):
            label = "copules : " + " + ".join(combo)
            tbl = copula_regression(sc, target, preds, list(combo), n_boot=n_boot, seed=seed)
            tbl.insert(0, "modèle", label)
            tables.append(tbl)
            identified = all(normality.loc[c, "non normal (p<0,05)"] for c in combo)
            for c in combo:
                row = tbl.loc[f"copule({c})"]
                if not identified:
                    # régresseur(s) ~ normal(aux) : la copule est quasi colinéaire au régresseur,
                    # l'estimation n'a pas de sens (Becker, Proksch & Ringle 2022)
                    verdict = "non interprétable (régresseur normal)"
                elif row["p_value"] < 0.05:
                    verdict = "endogénéité"
                else:
                    verdict = "pas d'endogénéité"
                summary.append({"modèle": label, "régresseur": c, "copule": row["coefficient"],
                                "p_value": row["p_value"], "chemin corrigé": tbl.loc[c, "coefficient"],
                                "chemin PLS": res.path_coefficients.loc[c, target],
                                "conclusion": verdict})
    return {"normality": normality, "models": pd.concat(tables), "summary": pd.DataFrame(summary)}
