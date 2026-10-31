"""Fonctions utilitaires de l'interface, sans dépendance à Streamlit (donc testables)."""
from __future__ import annotations

import io
import re
from collections import OrderedDict

import numpy as np
import pandas as pd

from .model import Model

_SUFFIX = re.compile(r"^(.*?)[_\-. ]?(\d+)$")


def guess_syntax(columns) -> str:
    """Propose un modèle de mesure en regroupant les colonnes par préfixe (sat1, sat_2… → SAT)."""
    groups: "OrderedDict[str, list[str]]" = OrderedDict()
    for col in columns:
        m = _SUFFIX.match(str(col))
        prefix = m.group(1) if m and m.group(1) else str(col)
        groups.setdefault(prefix, []).append(str(col))
    lines = ["# Modèle de mesure  ( =~ réflectif,  <~ formatif )"]
    for prefix, cols in groups.items():
        name = re.sub(r"\W", "_", prefix).strip("_").upper() or "LV"
        lines.append(f"{name} =~ " + " + ".join(cols))
    lines += ["", "# Modèle structurel  ( cible ~ source1 + source2 )", "# EXEMPLE ~ A + B"]
    return "\n".join(lines)


def _q(s: str) -> str:
    return '"' + str(s).replace('"', r"\"") + '"'


SIG_POS, SIG_NEG, NONSIG = "#2E5E9E", "#C0392B", "#9a9893"


def stars(p: float) -> str:
    """Convention des articles : *** p < 0,001 · ** p < 0,01 · * p < 0,05 · ns sinon."""
    if p is None or not np.isfinite(p):
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"


def fmt_p(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _edge_label(value: float, key, boot, mode: str) -> str:
    """Texte d'une flèche : coefficient (+ étoiles, p ou t si le bootstrap est disponible)."""
    if boot is None or key not in boot.index:
        return f"{value:.3f}"
    r = boot.loc[key]
    st = stars(r["p_value"])
    if mode == "p":
        return f"{value:.3f}\\n(p {fmt_p(r['p_value']) if r['p_value'] < 0.001 else '= ' + fmt_p(r['p_value'])})"
    if mode == "t":
        return f"{value:.3f}\\n(t = {r['t_value']:.2f})"
    return f"{value:.3f}{'' if st == 'ns' else st}" + (" ns" if st == "ns" else "")


def _edge_style(value: float, key, boot) -> str:
    if boot is None or key not in boot.index:
        return f'color="{SIG_POS}", fontcolor="{SIG_POS}"'
    p = boot.loc[key, "p_value"]
    if not (np.isfinite(p) and p < 0.05):
        return f'color="{NONSIG}", fontcolor="#6b6a66", style=dashed'
    c = SIG_POS if value >= 0 else SIG_NEG
    return f'color="{c}", fontcolor="{c}"'


def model_to_dot(model: Model, res=None, show_indicators: bool = True, boot: pd.DataFrame | None = None,
                 label_mode: str = "stars") -> str:
    """Diagramme Graphviz (DOT) du modèle, annoté des estimations si `res` est fourni.

    `boot` : tableau de bootstrap_statistics (index (type, nom)) ; les flèches portent alors
    des étoiles (ou p, ou t selon `label_mode` : "stars", "p", "t") et sont colorées :
    bleu = positif significatif, rouge = négatif significatif, gris pointillé = non significatif (5 %)."""
    lines = [
        "digraph G {",
        '  rankdir=LR; splines=true; nodesep=0.25; ranksep=0.9;',
        '  node [fontname="Helvetica", fontsize=11];',
        '  edge [fontname="Helvetica", fontsize=9, color="#555555"];',
    ]
    if res is not None:
        from .higher_order import structural_view

        r2 = structural_view(res).r_squared
        meas = res.measurement_result
    else:
        r2, meas = {}, None
    hoc_tbl = None
    if res is not None and getattr(model, "higher_order", None):
        from .higher_order import higher_order_measurement

        hoc_tbl = higher_order_measurement(res)["components"]
    for lv in model.latents:
        label = lv if lv not in r2 else f"{lv}\\nR² = {r2[lv]:.3f}"
        extra = ", peripheries=2" if lv in getattr(model, "higher_order", {}) else ""
        lines.append(
            f'  {_q("lv:" + lv)} [label={_q(label)}, shape=ellipse, style=filled, '
            f'fillcolor="#DCE8F7", color="#2E5E9E", penwidth=1.5{extra}];'
        )
    if show_indicators:
        for lv in model.latents:
            for ind in model.measurement.get(lv, []):
                lines.append(f'  {_q("mv:" + ind)} [label={_q(ind)}, shape=box, style=filled, '
                             f'fillcolor="#FFF6D6", color="#B8962E", fontsize=9, height=0.3];')
                lab = ""
                if res is not None:
                    if model.modes[lv] == "A":
                        val, key = meas.outer_loadings[(lv, ind)], ("outer_loading", f"{lv} -> {ind}")
                    else:
                        val, key = meas.outer_weights[(lv, ind)], ("outer_weight", f"{ind} -> {lv}")
                    lab = f", label={_q(_edge_label(val, key, boot, label_mode))}"
                    if boot is not None and key in boot.index and not boot.loc[key, "p_value"] < 0.05:
                        lab += f', style=dashed, color="{NONSIG}"'
                if model.modes[lv] == "A":
                    lines.append(f'  {_q("lv:" + lv)} -> {_q("mv:" + ind)} [arrowsize=0.6{lab}];')
                else:
                    lines.append(f'  {_q("mv:" + ind)} -> {_q("lv:" + lv)} [arrowsize=0.6{lab}];')
    for hoc, locs in getattr(model, "higher_order", {}).items():
        for loc in locs:
            lab = ""
            if hoc_tbl is not None:
                if model.modes[hoc] == "A":
                    val, key = hoc_tbl.loc[(hoc, loc), "chargement"], ("hoc_loading", f"{hoc} -> {loc}")
                else:
                    val, key = hoc_tbl.loc[(hoc, loc), "poids"], ("hoc_weight", f"{loc} -> {hoc}")
                lab = f", label={_q(_edge_label(val, key, boot, label_mode))}"
            a, b = (hoc, loc) if model.modes[hoc] == "A" else (loc, hoc)
            lines.append(f'  {_q("lv:" + a)} -> {_q("lv:" + b)} [color="#6b7280", fontcolor="#52514e", '
                         f'style=dashed, arrowsize=0.7{lab}];')
    for s, d in model.structural:
        attrs = f'color="{SIG_POS}", fontcolor="{SIG_POS}"'
        if res is not None:
            v = res.path_coefficients.loc[s, d]
            key = ("direct", f"{s} -> {d}")
            attrs = (_edge_style(v, key, boot) + f", label={_q(_edge_label(v, key, boot, label_mode))}"
                     f", penwidth={1 + 3 * min(abs(v), 1):.2f}")
        lines.append(f'  {_q("lv:" + s)} -> {_q("lv:" + d)} [{attrs}];')
    for a, b, d in getattr(model, "interactions", []):
        name = f"{a}:{b}"
        attrs = 'color="#B8962E", fontcolor="#8a6d1f", style=dashed'
        if res is not None and name in res.path_coefficients.index:
            v = res.path_coefficients.loc[name, d]
            key = ("direct", f"{name} -> {d}")
            attrs = _edge_style(v, key, boot) + f", label={_q(_edge_label(v, key, boot, label_mode))}"
            if boot is None or key not in boot.index:
                attrs = 'color="#B8962E", fontcolor="#8a6d1f", style=dashed' + f", label={_q(f'{v:.3f}')}"
        lines.append(f'  {_q("ix:" + name)} [label={_q(a + " × " + b)}, shape=diamond, style=filled, '
                     f'fillcolor="#FFF6D6", color="#B8962E", fontsize=9];')
        lines.append(f'  {_q("ix:" + name)} -> {_q("lv:" + d)} [{attrs}];')
    lines.append("}")
    return "\n".join(lines)


def to_excel(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Écrit plusieurs tableaux dans un classeur Excel (un onglet par tableau)."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in sheets.items():
            if df is None:
                continue
            out = df.copy()
            if isinstance(out.index, pd.MultiIndex):
                out = out.reset_index()
            out.to_excel(xw, sheet_name=name[:31])
    return buf.getvalue()


def prepare_data(df: pd.DataFrame, model: Model, keep: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Sélectionne les indicateurs, convertit en numérique, supprime les lignes incomplètes.

    `keep` : colonnes supplémentaires conservées telles quelles (ex. variable de groupe)."""
    warnings = []
    keep = [c for c in (keep or []) if c not in model.indicators]
    missing = [c for c in model.indicators + keep if c not in df.columns]
    if missing:
        raise KeyError(f"Colonnes introuvables dans les données : {', '.join(missing)}")
    sub = df[model.indicators].apply(pd.to_numeric, errors="coerce")
    for c in keep:
        sub[c] = df[c]
    n0 = len(sub)
    sub = sub.dropna()
    if len(sub) < n0:
        warnings.append(f"{n0 - len(sub)} ligne(s) avec valeurs manquantes ou non numériques supprimée(s) "
                        f"(suppression par liste) : {len(sub)} observations utilisées.")
    if len(sub) < 30:
        warnings.append("Moins de 30 observations : les résultats seront très instables.")
    return sub.reset_index(drop=True), warnings
