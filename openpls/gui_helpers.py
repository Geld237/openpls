"""Fonctions utilitaires de l'interface, sans dépendance à Streamlit (donc testables)."""
from __future__ import annotations

import io
import re
from collections import OrderedDict

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


def model_to_dot(model: Model, res=None, show_indicators: bool = True) -> str:
    """Diagramme Graphviz (DOT) du modèle, annoté des estimations si `res` est fourni."""
    lines = [
        "digraph G {",
        '  rankdir=LR; splines=true; nodesep=0.25; ranksep=0.9;',
        '  node [fontname="Helvetica", fontsize=11];',
        '  edge [fontname="Helvetica", fontsize=9, color="#555555"];',
    ]
    r2 = res.r_squared if res is not None else {}
    meas = res.measurement_result if res is not None else None
    for lv in model.latents:
        label = lv if lv not in r2 else f"{lv}\\nR² = {r2[lv]:.3f}"
        lines.append(
            f'  {_q("lv:" + lv)} [label={_q(label)}, shape=ellipse, style=filled, '
            f'fillcolor="#DCE8F7", color="#2E5E9E", penwidth=1.5];'
        )
    if show_indicators:
        for lv in model.latents:
            for ind in model.measurement[lv]:
                lines.append(f'  {_q("mv:" + ind)} [label={_q(ind)}, shape=box, style=filled, '
                             f'fillcolor="#FFF6D6", color="#B8962E", fontsize=9, height=0.3];')
                lab = ""
                if res is not None:
                    val = meas.outer_loadings[(lv, ind)] if model.modes[lv] == "A" else meas.outer_weights[(lv, ind)]
                    lab = f", label={_q(f'{val:.3f}')}"
                if model.modes[lv] == "A":
                    lines.append(f'  {_q("lv:" + lv)} -> {_q("mv:" + ind)} [arrowsize=0.6{lab}];')
                else:
                    lines.append(f'  {_q("mv:" + ind)} -> {_q("lv:" + lv)} [arrowsize=0.6{lab}];')
    for s, d in model.structural:
        lab = ""
        if res is not None:
            v = res.path_coefficients.loc[s, d]
            lab = f", label={_q(f'{v:.3f}')}, penwidth={1 + 3 * min(abs(v), 1):.2f}"
        lines.append(f'  {_q("lv:" + s)} -> {_q("lv:" + d)} [color="#2E5E9E", fontcolor="#2E5E9E"{lab}];')
    for a, b, d in getattr(model, "interactions", []):
        name = f"{a}:{b}"
        lab = ""
        if res is not None and name in res.path_coefficients.index:
            v = res.path_coefficients.loc[name, d]
            lab = f", label={_q(f'{v:.3f}')}"
        lines.append(f'  {_q("ix:" + name)} [label={_q(a + " × " + b)}, shape=diamond, style=filled, '
                     f'fillcolor="#FFF6D6", color="#B8962E", fontsize=9];')
        lines.append(f'  {_q("ix:" + name)} -> {_q("lv:" + d)} [color="#B8962E", fontcolor="#8a6d1f", style=dashed{lab}];')
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
