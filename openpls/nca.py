"""Analyse des conditions nécessaires (NCA ; Dul 2016 ; Richter et al. 2020).

Question : X est-il NÉCESSAIRE à Y (pas de Y élevé sans X suffisant) ?
* Plafond CE-FDH (enveloppe de libre disposition, en escalier) :
  c(x) = max { y_i : x_i <= x }.
* Zone vide = aire au-dessus du plafond dans le rectangle [min x, max x] × [min y, max y].
* Taille d'effet d = zone vide / aire du rectangle (0 ≤ d ≤ 1) ; repères de Dul :
  0-0,1 faible, 0,1-0,3 moyen, 0,3-0,5 fort, ≥ 0,5 très fort.
* Significativité : test de permutation (Dul et al. 2020), Y permuté par rapport à X.
* Tableau des goulots : niveau de X requis (en % de son étendue) pour atteindre chaque
  niveau de Y (en % de son étendue). Le tableau est invariant aux changements d'échelle
  linéaires : on peut l'appliquer aux scores standardisés ou 0-100 des latentes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ce_fdh_effect(x: np.ndarray, y: np.ndarray) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
    scope = (xmax - xmin) * (ymax - ymin)
    if scope <= 0:
        return np.nan
    order = np.argsort(x, kind="mergesort")
    xs, ys = x[order], y[order]
    ux, first = np.unique(xs, return_index=True)
    # max de y pour chaque valeur unique de x, puis maximum cumulé = hauteur du plafond
    grp_max = np.maximum.reduceat(ys, first)
    ceiling = np.maximum.accumulate(grp_max)
    widths = np.diff(np.append(ux, xmax))
    return float(((ymax - ceiling) * widths).sum() / scope)


def bottleneck(x: np.ndarray, y: np.ndarray, steps=range(0, 101, 10)) -> pd.Series:
    """Niveau minimal de X (% de son étendue) requis pour chaque niveau de Y (% de son étendue).
    NaN = « NN » (non nécessaire : le minimum de X suffit)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    xmin, xr, ymin, yr = x.min(), np.ptp(x), y.min(), np.ptp(y)
    out = {}
    for s in steps:
        level = ymin + yr * s / 100
        need = x[y >= level - 1e-12].min()
        pct = 100 * (need - xmin) / xr if xr > 0 else 0.0
        out[f"{s} %"] = pct if pct > 1e-9 else np.nan
    return pd.Series(out, name="X requis (%)")


def nca_test(x, y, n_perm: int = 1000, seed: int | None = 42) -> dict:
    rng = np.random.default_rng(seed)
    x, y = np.asarray(x, float), np.asarray(y, float)
    d = ce_fdh_effect(x, y)
    perm = np.array([ce_fdh_effect(x, rng.permutation(y)) for _ in range(n_perm)])
    p = ((perm >= d - 1e-12).sum() + 1) / (n_perm + 1)
    return {"d": d, "p_value": p}


def effect_label(d: float) -> str:
    if not np.isfinite(d):
        return "—"
    return ("faible" if d < 0.1 else "moyen" if d < 0.3 else "fort" if d < 0.5 else "très fort")


def nca(res, target: str, n_perm: int = 1000, seed: int | None = 42, scores: pd.DataFrame | None = None) -> dict:
    """NCA de chaque prédécesseur de `target` sur les scores des latentes.

    `scores` : par défaut les scores standardisés de res ; on peut passer les scores 0-100 de l'IPMA
    (identique pour d et le tableau des goulots, qui sont invariants d'échelle)."""
    model = res.model
    if target not in model.latents:
        raise KeyError(f"Latente inconnue : {target}")
    sc = res.scores if scores is None else scores
    j = model.latents.index(target)
    preds = [model.latents[i] for i in model.predecessors(j) if ":" not in model.latents[i]]
    if not preds:
        raise ValueError(f"{target} n'a aucun prédécesseur")
    rows, bn = {}, {}
    for k, lv in enumerate(preds):
        t = nca_test(sc[lv], sc[target], n_perm=n_perm, seed=None if seed is None else seed + k)
        rows[lv] = {"d (CE-FDH)": t["d"], "taille": effect_label(t["d"]), "p_value": t["p_value"],
                    "condition nécessaire (d≥0,1 et p<0,05)": bool(t["d"] >= 0.1 and t["p_value"] < 0.05)}
        bn[lv] = bottleneck(sc[lv].to_numpy(), sc[target].to_numpy())
    bn_tbl = pd.DataFrame(bn)
    bn_tbl.index.name = f"{target} (%)"
    return {"effects": pd.DataFrame.from_dict(rows, orient="index"), "bottleneck": bn_tbl.astype(float)}
