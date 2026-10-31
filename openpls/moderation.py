"""Modération (effets d'interaction) en PLS-SEM.

Trois approches classiques (Henseler & Chin 2010 ; Becker, Ringle & Sarstedt 2018 ;
Hair et al. 2022, chap. 7) :

* "two_stage" (défaut, recommandé) — étape 1 : on estime le modèle sans interaction et on
  récupère les scores des variables latentes ; étape 2 : chaque latente devient un construit
  à indicateur unique (son score) et le terme d'interaction est le produit des scores
  standardisés de X et M. Fonctionne aussi avec des construits formatifs.
* "product_indicator" — l'interaction est mesurée par tous les produits deux à deux des
  indicateurs standardisés de X et de M (construits réflectifs uniquement).
* "orthogonal" — comme product_indicator, mais chaque produit est remplacé par son résidu
  après régression sur tous les indicateurs de X et M (Little, Bovaird & Widaman 2006).

Le terme d'interaction apparaît dans les résultats comme une latente nommée "X:M".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .model import Model

METHODS = ("two_stage", "product_indicator", "orthogonal")


def _z(v: np.ndarray) -> np.ndarray:
    return (v - v.mean(axis=0)) / v.std(axis=0, ddof=1)


def interaction_name(a: str, b: str) -> str:
    return f"{a}:{b}"


def fit_moderated(data: pd.DataFrame, model: Model, method: str = "two_stage", **fit_kwargs):
    from .algorithm import _fit_plain

    if method not in METHODS:
        raise ValueError(f"Méthode de modération inconnue : {method} (choix : {', '.join(METHODS)})")
    base = model.without_interactions()
    missing = [c for c in base.indicators if c not in data.columns]
    if missing:
        raise KeyError(f"Indicateurs absents des données : {missing}")

    if method == "two_stage":
        stage1 = _fit_plain(data, base, **fit_kwargs)
        cols, measurement = {}, {}
        for lv in base.latents:
            cols[f"{lv}__score"] = stage1.scores[lv].to_numpy()
            measurement[lv] = [f"{lv}__score"]
        for a, b, _ in model.interactions:
            name = interaction_name(a, b)
            if name in measurement:
                continue
            cols[f"{name}__score"] = _z(stage1.scores[a].to_numpy()) * _z(stage1.scores[b].to_numpy())
            measurement[name] = [f"{name}__score"]
        aug_data = pd.DataFrame(cols, index=data.index)
        # étape 2 : indicateurs uniques, estimés en PLS ; la correction PLSc éventuelle est appliquée
        # ensuite sur les corrélations (Becker, Ringle & Sarstedt 2018)
        kw2 = {**fit_kwargs, "consistent": False}
        modes = {lv: "A" for lv in measurement}
    else:
        stage1 = None
        x = data[base.indicators].astype(float)
        x = (x - x.mean()) / x.std(ddof=1)
        cols = {c: x[c].to_numpy() for c in base.indicators}
        measurement = {lv: list(base.measurement[lv]) for lv in base.latents}
        modes = dict(base.modes)
        for a, b, _ in model.interactions:
            name = interaction_name(a, b)
            if name in measurement:
                continue
            for lv in (a, b):
                if base.modes[lv] != "A":
                    raise ValueError(f"L'approche « {method} » exige des construits réflectifs ({lv} est formatif) : "
                                     "utilise l'approche en deux étapes.")
            ia, ib = base.measurement[a], base.measurement[b]
            prods = {f"{i}*{j}": x[i].to_numpy() * x[j].to_numpy() for i in ia for j in ib}
            if method == "orthogonal":
                design = np.column_stack([np.ones(len(x)), x[ia + ib].to_numpy()])
                for k, v in prods.items():
                    beta = np.linalg.lstsq(design, v, rcond=None)[0]
                    prods[k] = v - design @ beta
            cols.update(prods)
            measurement[name] = list(prods)
            modes[name] = "A"
        aug_data = pd.DataFrame(cols, index=data.index)
        kw2 = fit_kwargs

    structural = list(base.structural)
    for a, b, dst in model.interactions:
        structural.append((interaction_name(a, b), dst))
    aug_model = Model(measurement, structural, modes)
    res = _fit_plain(aug_data, aug_model, **kw2)
    res.spec = model
    res.stage1 = stage1
    res.moderation = method
    names = {interaction_name(a, b): (a, b) for a, b, _ in model.interactions}

    if method == "two_stage" and fit_kwargs.get("consistent"):
        # PLSc en deux étapes : fiabilités de l'étape 1 (rho_A) pour les effets simples ; pour le produit
        # de deux composites standardisés (normalité), rel(XM) = (ρX·ρM + r²) / (1 + r²), r = corr(X̂, M̂)
        lvs = aug_model.latents
        r = res.scores[lvs].corr().to_numpy()
        rel = np.array([1.0 if lv in names else float(stage1.rho_a[lv]) for lv in lvs])
        for name, (a, b) in names.items():
            rab = r[lvs.index(a), lvs.index(b)]
            rel[lvs.index(name)] = (rel[lvs.index(a)] * rel[lvs.index(b)] + rab**2) / (1 + rab**2)
        r_lat = r / np.sqrt(np.outer(rel, rel))
        np.fill_diagonal(r_lat, 1.0)
        from .algorithm import _structural_from_corr

        paths, r2 = _structural_from_corr(aug_model, r_lat)
        res.path_coefficients = pd.DataFrame(paths, index=lvs, columns=lvs)
        res.r_squared = pd.Series(r2)
        res.rho_a = pd.Series(rel, index=lvs)
        res.latent_correlations = pd.DataFrame(r_lat, index=lvs, columns=lvs)
        res.consistent = True

    # échelle du terme d'interaction : le produit Z_X·Z_M (moyenne r, écart-type ≈ √(1 + r²)) est
    # re-standardisé dans le modèle ; il faut le savoir pour calculer les pentes simples
    res.interaction_scale = {}
    for name, (a, b) in names.items():
        if res.consistent and res.latent_correlations is not None:
            rab = float(res.latent_correlations.loc[a, b])
            res.interaction_scale[name] = (rab, float(np.sqrt(1 + rab**2)))
        else:
            src = res.stage1.scores if res.stage1 is not None else res.scores
            prod = _z(src[a].to_numpy()) * _z(src[b].to_numpy())
            res.interaction_scale[name] = (float(prod.mean()), float(prod.std(ddof=1)))
    return res


def simple_slopes(res, x: str, m: str, target: str, levels=(-1.0, 0.0, 1.0)) -> pd.DataFrame:
    """Pente de X sur la cible pour plusieurs niveaux du modérateur M (en écarts-types).

    Le terme d'interaction du modèle est le produit standardisé (X·M - μ) / σ, avec μ = corr(X, M)
    et σ ≈ √(1 + corr²). Avec Y = b_x X + b_m M + b_xm (X·M - μ)/σ, la pente de X quand M = m vaut
    b_x + b_xm · m / σ (σ = 1 seulement si X et M sont non corrélés)."""
    pc = res.path_coefficients
    name = interaction_name(x, m) if interaction_name(x, m) in pc.index else interaction_name(m, x)
    if name not in pc.index:
        raise KeyError(f"Pas d'interaction entre {x} et {m}")
    bx, bm, bxm = pc.loc[x, target], pc.loc[m, target], pc.loc[name, target]
    mu, sd = getattr(res, "interaction_scale", {}).get(name, (0.0, 1.0))
    if x == m:  # effet quadratique : Y = b X + q (X² - μ)/σ ; pente en X = x0 : b + 2 q x0 / σ
        rows = [{f"{m} (ET)": lvl, "pente": bx + 2 * bxm * lvl / sd,
                 f"{target} si {x}=-1": bx * -1.0 + bxm * (1.0 - mu) / sd,
                 f"{target} si {x}=+1": bx * 1.0 + bxm * (1.0 - mu) / sd} for lvl in levels]
        return pd.DataFrame(rows).set_index(f"{m} (ET)")
    rows = []
    for lvl in levels:
        pred = lambda xv: bx * xv + bm * lvl + bxm * (xv * lvl - mu) / sd  # noqa: E731
        rows.append({
            f"{m} (ET)": lvl,
            "pente": bx + bxm * lvl / sd,
            f"{target} si {x}=-1": pred(-1.0),
            f"{target} si {x}=+1": pred(1.0),
        })
    return pd.DataFrame(rows).set_index(f"{m} (ET)")


def simple_slope_statistics(res) -> pd.Series:
    """Pentes simples à M = -1, 0, +1 ET pour chaque interaction (pour le bootstrap)."""
    spec = res.spec or res.model
    out = {}
    for a, b, dst in spec.interactions:
        tbl = simple_slopes(res, a, b, dst)
        for lvl, slope in tbl["pente"].items():
            out[("simple_slope", f"{a} -> {dst} | {b} = {lvl:+.0f} ET")] = slope
    return pd.Series(out, dtype=float)
