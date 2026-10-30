"""Analyse importance-performance (IPMA ; Ringle & Sarstedt 2016).

1. Chaque indicateur est ramené sur une échelle 0-100 :
   100 · (x - min_échelle) / (max_échelle - min_échelle)
   (bornes théoriques de l'échelle si fournies, sinon min/max observés).
2. Les poids externes standardisés sont « déstandardisés » (w / écart-type) puis normalisés
   pour sommer à 1 dans chaque bloc : le score de la latente est alors une moyenne pondérée
   des indicateurs et reste sur 0-100. Les poids doivent être positifs.
3. Performance = moyenne du score 0-100 de la latente.
4. Importance = effet total NON standardisé sur la cible, obtenu en régressant (MCO avec
   constante) chaque latente endogène sur ses prédécesseurs, scores 0-100.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .model import Model


def rescaled_scores(res, data: pd.DataFrame, scale: tuple[float, float] | dict | None = None):
    """Scores des latentes sur 0-100 et poids déstandardisés normalisés. Retourne (scores, poids)."""
    model = res.model
    if res.spec is not None and res.spec.higher_order:
        raise ValueError("IPMA non disponible pour les modèles d'ordre supérieur")
    if model.interactions or res.spec is not None:
        raise ValueError("IPMA non disponible pour les modèles avec interaction")
    cols = model.indicators
    x = data[cols].astype(float)
    lo, hi = {}, {}
    for c in cols:
        if scale is None:
            lo[c], hi[c] = x[c].min(), x[c].max()
        elif isinstance(scale, dict):
            lo[c], hi[c] = scale[c]
        else:
            lo[c], hi[c] = scale
        if hi[c] <= lo[c]:
            raise ValueError(f"Bornes d'échelle invalides pour {c}")
    x100 = pd.DataFrame({c: 100 * (x[c] - lo[c]) / (hi[c] - lo[c]) for c in cols}, index=x.index)

    sd = x100.std(ddof=1)
    scores, weights = {}, {}
    for lv in model.latents:
        w = res.outer_weights[lv]
        if (w <= 0).any():
            bad = ", ".join(w.index[w <= 0])
            raise ValueError(f"IPMA : poids négatif ou nul dans {lv} ({bad}) ; l'IPMA exige des poids positifs")
        raw = w / sd[w.index]
        rw = raw / raw.sum()
        weights[lv] = rw
        scores[lv] = x100[list(rw.index)].to_numpy() @ rw.to_numpy()
    idx = pd.MultiIndex.from_tuples([(lv, i) for lv in model.latents for i in weights[lv].index],
                                    names=["latent", "indicator"])
    w_all = pd.Series(np.concatenate([weights[lv].to_numpy() for lv in model.latents]), index=idx)
    return pd.DataFrame(scores, index=data.index), w_all


def unstandardized_total_effects(model: Model, scores: pd.DataFrame) -> pd.DataFrame:
    lvs = model.latents
    k = len(lvs)
    b = np.zeros((k, k))
    for j in model.endogenous():
        pred = model.predecessors(j)
        design = np.column_stack([np.ones(len(scores)), scores.iloc[:, pred].to_numpy()])
        coef = np.linalg.lstsq(design, scores.iloc[:, j].to_numpy(), rcond=None)[0]
        b[pred, j] = coef[1:]
    t = np.linalg.inv(np.eye(k) - b) - np.eye(k)
    return pd.DataFrame(t, index=lvs, columns=lvs)


def ipma(res, data: pd.DataFrame, target: str, scale=None) -> dict[str, pd.DataFrame]:
    """IPMA pour la latente `target`. Retourne {"latents": importance/performance par
    antécédent, "indicators": idem par indicateur, "scores": scores 0-100}."""
    model = res.model
    if target not in model.latents:
        raise KeyError(f"Latente inconnue : {target}")
    scores, w = rescaled_scores(res, data, scale)
    t = unstandardized_total_effects(model, scores)
    perf = scores.mean()
    ante = [lv for lv in model.latents if abs(t.loc[lv, target]) > 0 and lv != target]
    if not ante:
        raise ValueError(f"{target} n'a aucun antécédent")
    lat = pd.DataFrame({"importance": t.loc[ante, target], "performance": perf[ante]})
    lat.index.name = "latente"
    rows = []
    for lv in ante:
        for ind, wi in w[lv].items():
            if scale is None:
                lo, hi = data[ind].min(), data[ind].max()
            else:
                lo, hi = scale[ind] if isinstance(scale, dict) else scale
            rows.append({"latente": lv, "indicateur": ind, "importance": t.loc[lv, target] * wi,
                         "performance": 100 * (data[ind].astype(float).mean() - lo) / (hi - lo)})
    ind_tbl = pd.DataFrame(rows)
    ind_tbl = ind_tbl.set_index(["latente", "indicateur"])
    return {"latents": lat, "indicators": ind_tbl, "scores": scores, "target_performance": float(perf[target])}
