"""Critères d'évaluation du modèle de mesure (Hair et al., Henseler et al. 2015)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _measured(res) -> list[str]:
    """Latentes dont le modèle de mesure s'évalue directement : hors termes d'interaction X:M
    et hors construits d'ordre supérieur (évalués par openpls.higher_order)."""
    spec = getattr(res, "spec", None)
    hoc = set(spec.higher_order) if spec is not None else set()
    return [lv for lv in res.model.latents if ":" not in lv and lv not in hoc]


def quality_criteria(res) -> pd.DataFrame:
    """Alpha de Cronbach, fiabilité composite (rho_c) et AVE pour chaque latente réflective."""
    rows = {}
    for lv in _measured(res):
        inds = res.model.measurement[lv]
        lam = res.outer_loadings[lv].to_numpy()
        x = res.data_std[inds].to_numpy()
        m = len(inds)
        if m > 1:
            item_var = x.var(axis=0, ddof=1).sum()
            total_var = x.sum(axis=1).var(ddof=1)
            alpha = m / (m - 1) * (1 - item_var / total_var)
        else:
            alpha = np.nan
        s = lam.sum() ** 2
        rho_c = s / (s + (1 - lam**2).sum())
        ave = (lam**2).mean()
        if res.model.modes[lv] == "B":  # critères de fiabilité sans objet pour un bloc formatif
            alpha = rho_c = ave = np.nan
            rho_a_lv = np.nan
        else:
            rho_a_lv = res.rho_a[lv]
        rows[lv] = {"cronbach_alpha": alpha, "rho_A": rho_a_lv, "rho_c": rho_c, "AVE": ave}
    return pd.DataFrame(rows).T


def fornell_larcker(res) -> pd.DataFrame:
    """Diagonale = racine de l'AVE, hors diagonale = corrélations entre latentes."""
    lvs = _measured(res)
    # en PLSc, l'AVE vient des chargements corrigés : on la compare aux corrélations corrigées
    if res.consistent and res.latent_correlations is not None:
        corr = res.latent_correlations.loc[lvs, lvs].copy()
    else:
        corr = res.scores[lvs].corr()
    ave = quality_criteria(res)["AVE"]
    out = corr.copy()
    for lv in out.index:
        out.loc[lv, lv] = np.sqrt(ave[lv])
    return out


def htmt(res) -> pd.DataFrame:
    """Ratio heterotrait-monotrait (Henseler, Ringle & Sarstedt 2015). Seuil usuel : < 0.85 / 0.90."""
    lvs = _measured(res)
    corr = res.data_std.corr().abs()
    out = pd.DataFrame(np.nan, index=lvs, columns=lvs)

    def mono(lv):
        inds = res.model.measurement[lv]
        if len(inds) < 2:
            return np.nan
        c = corr.loc[inds, inds].to_numpy()
        return c[np.triu_indices(len(inds), 1)].mean()

    for a_i, a in enumerate(lvs):
        for b in lvs[a_i + 1 :]:
            hetero = corr.loc[res.model.measurement[a], res.model.measurement[b]].to_numpy().mean()
            val = hetero / np.sqrt(mono(a) * mono(b))
            out.loc[b, a] = val
    return out


def f_squared(res, data, **fit_kwargs) -> pd.DataFrame:
    """Taille d'effet f² : (R²_inclus - R²_exclu) / (1 - R²_inclus)."""
    from .algorithm import fit
    from .model import Model

    from .higher_order import structural_view

    spec = res.spec or res.model
    # les modèles réduits sont estimés avec les mêmes réglages que `res`
    inherited = {"consistent": res.consistent, "scheme": res.scheme}
    for attr in ("moderation", "hoc_method"):
        if getattr(res, attr, None):
            inherited[attr] = getattr(res, attr)
    fit_kwargs = {**inherited, **fit_kwargs}
    view = structural_view(res)
    rows = []
    for src, dst in view.model.structural:
        if ":" in src:  # terme d'interaction : on retire seulement l'interaction
            structural = list(spec.structural)
            inter = [i for i in spec.interactions if not (f"{i[0]}:{i[1]}" == src and i[2] == dst)]
        else:  # effet simple : on retire aussi les interactions qui en dépendent
            structural = [p for p in spec.structural if p != (src, dst)]
            inter = [i for i in spec.interactions if not (i[2] == dst and src in i[:2])]
        r2_in = res.r_squared[dst]
        if not any(d == dst for _, d in structural) and not any(i[2] == dst for i in inter):
            r2_out = 0.0
        else:
            sub = fit(data, Model(spec.measurement, structural, dict(spec.modes), inter,
                                  dict(spec.higher_order)), **fit_kwargs)
            r2_out = sub.r_squared[dst]
        rows.append({"path": f"{src} -> {dst}", "f2": (r2_in - r2_out) / (1 - r2_in)})
    return pd.DataFrame(rows).set_index("path")


def measurement_statistics(res) -> pd.Series:
    """Chargements et poids externes (construits d'ordre 1), pour le bootstrap.

    Clés : ("outer_loading", "LV -> indicateur") et ("outer_weight", "indicateur -> LV")."""
    meas = res.measurement_result
    out = {}
    for lv in _measured(meas):
        for ind in meas.model.measurement[lv]:
            out[("outer_loading", f"{lv} -> {ind}")] = meas.outer_loadings[(lv, ind)]
            out[("outer_weight", f"{ind} -> {lv}")] = meas.outer_weights[(lv, ind)]
    return pd.Series(out, dtype=float)
