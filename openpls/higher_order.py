"""Construits d'ordre supérieur (second ordre) en PLS-SEM.

Syntaxe : un bloc dont tous les termes sont des variables latentes définit un construit
d'ordre supérieur (HOC) ; ses termes sont ses composantes d'ordre 1 (LOC).

    Qualite =~ Fiabilite + Reactivite + Empathie     # HOC réflectif-réflectif
    Valeur  <~ Prix + Commodite                      # HOC réflectif-formatif

Trois approches d'estimation (Becker, Klein & Wetzels 2012 ; Sarstedt et al. 2019 ;
Hair et al. 2018, chap. 2) :

* "two_stage_disjoint" (défaut) — étape 1 : le HOC est retiré et ses composantes sont
  reliées directement aux antécédents et conséquences du HOC ; étape 2 : les scores des
  composantes deviennent les indicateurs du HOC.
* "two_stage_embedded" — étape 1 : modèle à indicateurs répétés ; étape 2 : comme ci-dessus.
* "repeated_indicators" — le HOC est mesuré par tous les indicateurs de ses composantes,
  et relié à elles par des chemins (HOC -> LOC si réflectif, LOC -> HOC si formatif).
  Ces chemins sont des relations de MESURE : ils sont exclus des effets structurels.

Évaluation du HOC : ses composantes jouent le rôle d'indicateurs (chargements, poids,
fiabilité, AVE ; VIF pour un HOC formatif) — voir `higher_order_measurement`.
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from .model import Model

METHODS = ("two_stage_disjoint", "two_stage_embedded", "repeated_indicators")


def _rep(ind: str, hoc: str) -> str:
    return f"{ind}@{hoc}"


def _repeated(spec: Model, data: pd.DataFrame):
    measurement = {lv: list(v) for lv, v in spec.measurement.items()}
    structural = list(spec.structural)
    cols = {}
    for hoc, locs in spec.higher_order.items():
        inds = []
        for loc in locs:
            for i in spec.measurement[loc]:
                cols[_rep(i, hoc)] = data[i]
                inds.append(_rep(i, hoc))
        measurement[hoc] = inds
        for loc in locs:
            structural.append((hoc, loc) if spec.modes[hoc] == "A" else (loc, hoc))
    aug = pd.concat([data[spec.indicators], pd.DataFrame(cols, index=data.index)], axis=1)
    return Model(measurement, structural, dict(spec.modes)), aug


def _disjoint(spec: Model, data: pd.DataFrame):
    expand = lambda lv: spec.higher_order.get(lv, [lv])  # noqa: E731
    structural = []
    for s, d in spec.structural:
        for a in expand(s):
            for b in expand(d):
                if (a, b) not in structural:
                    structural.append((a, b))
    modes = {lv: spec.modes[lv] for lv in spec.measurement}
    return Model(dict(spec.measurement), structural, modes), data[spec.indicators]


def fit_higher_order(data: pd.DataFrame, spec: Model, method: str = "two_stage_disjoint", **fit_kwargs):
    from .algorithm import _fit_plain

    if method not in METHODS:
        raise ValueError(f"Approche d'ordre supérieur inconnue : {method} (choix : {', '.join(METHODS)})")
    missing = [c for c in spec.indicators if c not in data.columns]
    if missing:
        raise KeyError(f"Indicateurs absents des données : {missing}")

    if method == "repeated_indicators":
        m, d = _repeated(spec, data)
        res = _fit_plain(d, m, **fit_kwargs)
        res.spec, res.hoc_method = spec, method
        return res

    m1, d1 = (_disjoint if method == "two_stage_disjoint" else _repeated)(spec, data)
    stage1 = _fit_plain(d1, m1, **fit_kwargs)
    stage1.spec, stage1.hoc_method = spec, method
    comp = spec.components()
    measurement, cols = {}, {}
    for lv in spec.latents:
        if lv in comp:
            continue
        if lv in spec.higher_order:
            measurement[lv] = [f"{loc}__score" for loc in spec.higher_order[lv]]
            for loc in spec.higher_order[lv]:
                cols[f"{loc}__score"] = stage1.scores[loc].to_numpy()
        else:
            measurement[lv] = list(spec.measurement[lv])
            for c in measurement[lv]:
                cols[c] = data[c].to_numpy()
    m2 = Model(measurement, list(spec.structural), {lv: spec.modes[lv] for lv in measurement})
    res = _fit_plain(pd.DataFrame(cols, index=data.index), m2, **fit_kwargs)
    res.spec, res.stage1, res.hoc_method = spec, stage1, method
    return res


# ---------------------------------------------------------------- vue structurelle
def measurement_edges(res) -> set[tuple[str, str]]:
    """Relations HOC <-> composantes présentes dans res.model (approche à indicateurs répétés)."""
    spec = getattr(res, "spec", None)
    if spec is None or not spec.higher_order:
        return set()
    edges = set()
    for hoc, locs in spec.higher_order.items():
        for loc in locs:
            edges |= {(hoc, loc), (loc, hoc)}
    return {e for e in edges if e in set(res.model.structural)}


def structural_view(res):
    """Copie de `res` limitée au modèle structurel : les chemins HOC <-> composantes
    (relations de mesure) sont retirés. Renvoie `res` lui-même si rien à retirer."""
    edges = measurement_edges(res)
    if not edges:
        return res
    m = res.model
    view = copy.copy(res)
    view.model = Model(m.measurement, [p for p in m.structural if p not in edges], dict(m.modes))
    pc = res.path_coefficients.copy()
    for s, d in edges:
        pc.loc[s, d] = 0.0
    view.path_coefficients = pc
    view.r_squared = res.r_squared[[lv for lv in res.r_squared.index if lv in
                                    [view.model.latents[j] for j in view.model.endogenous()]]]
    return view


# ---------------------------------------------------------------- évaluation du HOC
def _vif(x: np.ndarray) -> np.ndarray:
    out = []
    for j in range(x.shape[1]):
        others = np.delete(x, j, axis=1)
        design = np.column_stack([np.ones(len(x)), others])
        beta = np.linalg.lstsq(design, x[:, j], rcond=None)[0]
        resid = x[:, j] - design @ beta
        r2 = 1 - resid.var() / x[:, j].var()
        out.append(1 / (1 - r2) if r2 < 1 else np.inf)
    return np.array(out)


def higher_order_measurement(res) -> dict[str, pd.DataFrame]:
    """{"components": une ligne par (HOC, composante), "quality": une ligne par HOC}.

    chargement = corrélation entre le score de la composante et celui du HOC ;
    poids = poids externe (deux étapes) ou coefficient LOC -> HOC (indicateurs répétés, formatif)."""
    spec = res.spec
    if spec is None or not spec.higher_order:
        raise ValueError("Le modèle n'a pas de construit d'ordre supérieur")
    loc_scores = res.stage1.scores if res.stage1 is not None else res.scores
    rows, qual = [], {}
    for hoc, locs in spec.higher_order.items():
        h = res.scores[hoc].to_numpy()
        x = loc_scores[locs].to_numpy()
        lam = np.array([np.corrcoef(x[:, k], h)[0, 1] for k in range(len(locs))])
        if res.stage1 is not None:
            w = np.array([res.outer_weights[(hoc, f"{loc}__score")] for loc in locs])
        elif spec.modes[hoc] == "B":
            w = np.array([res.path_coefficients.loc[loc, hoc] for loc in locs])
        else:
            w = np.full(len(locs), np.nan)
        vif = _vif(x)
        for k, loc in enumerate(locs):
            rows.append({"construit": hoc, "composante": loc, "chargement": lam[k], "poids": w[k], "VIF": vif[k]})
        if spec.modes[hoc] == "A":
            xs = (x - x.mean(0)) / x.std(0, ddof=1)
            m = len(locs)
            alpha = m / (m - 1) * (1 - xs.var(axis=0, ddof=1).sum() / xs.sum(axis=1).var(ddof=1))
            s = lam.sum() ** 2
            qual[hoc] = {"type": "réflectif", "cronbach_alpha": alpha, "rho_c": s / (s + (1 - lam**2).sum()),
                         "AVE": float((lam**2).mean()), "VIF max": float(vif.max())}
        else:
            qual[hoc] = {"type": "formatif", "cronbach_alpha": np.nan, "rho_c": np.nan, "AVE": np.nan,
                         "VIF max": float(vif.max())}
    return {"components": pd.DataFrame(rows).set_index(["construit", "composante"]),
            "quality": pd.DataFrame.from_dict(qual, orient="index")}


def higher_order_statistics(res) -> pd.Series:
    """Chargements (HOC réflectif) ou poids (HOC formatif) des composantes, pour le bootstrap."""
    tbl = higher_order_measurement(res)["components"]
    out = {}
    for (hoc, loc), r in tbl.iterrows():
        if res.spec.modes[hoc] == "A":
            out[("hoc_loading", f"{hoc} -> {loc}")] = r["chargement"]
        else:
            out[("hoc_weight", f"{loc} -> {hoc}")] = r["poids"]
    return pd.Series(out, dtype=float)
