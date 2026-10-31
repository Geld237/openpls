"""Fonctions utilitaires de l'interface, sans dépendance à Streamlit (donc testables)."""
from __future__ import annotations

import io
import re
from collections import OrderedDict

import html

import numpy as np
import pandas as pd

from .i18n import T
from .model import Model

_SUFFIX = re.compile(r"^(.*?)[_\-. ]?(\d+)$")


def guess_syntax(columns) -> str:
    """Propose un modèle de mesure en regroupant les colonnes par préfixe (sat1, sat_2… → SAT)."""
    groups: "OrderedDict[str, list[str]]" = OrderedDict()
    for col in columns:
        m = _SUFFIX.match(str(col))
        prefix = m.group(1) if m and m.group(1) else str(col)
        groups.setdefault(prefix, []).append(str(col))
    lines = [T("# Modèle de mesure  ( =~ réflectif,  <~ formatif )")]
    for prefix, cols in groups.items():
        name = re.sub(r"\W", "_", prefix).strip("_").upper() or "LV"
        lines.append(f"{name} =~ " + " + ".join(cols))
    lines += ["", T("# Modèle structurel  ( cible ~ source1 + source2 )"), T("# EXEMPLE ~ A + B")]
    return "\n".join(lines)


def _q(s: str) -> str:
    return '"' + str(s).replace('"', r"\"") + '"'


LABEL_BG = "#F5F7FA"  # fond du cadre du diagramme : une flèche qui croise un chiffre passe derrière lui


def _halo(text: str) -> str:
    """Étiquette de flèche sur un petit fond opaque (les flèches sont dessinées avant les étiquettes)."""
    return (f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1" BGCOLOR="{LABEL_BG}">'
            f'<TR><TD>{html.escape(str(text))}</TD></TR></TABLE>>')


SIG_POS, SIG_NEG, NONSIG = "#2E5E9E", "#B83A2E", "#98A2B3"


DECIMAL = "."  # séparateur décimal de l'affichage ; fixé par l'application (set_decimal)


def set_decimal(sep: str) -> None:
    global DECIMAL
    DECIMAL = "," if sep == "," else "."


def num(v: float, digits: int = 3) -> str:
    """Nombre formaté avec le séparateur décimal choisi (0,318 ou 0.318)."""
    s = f"{v:.{digits}f}"
    return s.replace(".", ",") if DECIMAL == "," else s


def stars(p: float, alpha: float | None = None) -> str:
    """Les trois seuils à la fois : *** p < 0,01 · ** p < 0,05 · * p < 0,10 ; sinon ns.
    (`alpha` est accepté pour compatibilité, il ne change pas les étoiles.)"""
    if p is None or not np.isfinite(p):
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return "ns"


def stars_legend(alpha: float | None = None) -> str:
    return f"*** p < {num(0.01, 2)}, ** p < {num(0.05, 2)}, * p < {num(0.10, 2)}, " + T("ns non significatif")


def fmt_p(p: float) -> str:
    return f"< {num(0.001)}" if p < 0.001 else num(p)


SIG_GREEN, SIG_RED = "#2F7D4F", "#B83A2E"


def _edge_label(value: float, key, boot, mode: str, alpha: float = 0.05) -> str:
    """Texte d'une flèche : coefficient, suivi des étoiles en mode « stars »."""
    if boot is None or key not in boot.index or mode != "stars":
        return num(value)
    return f"{num(value)}{stars(boot.loc[key, 'p_value'])}".replace("ns", " ns")


def _significant(key, boot, mode: str, alpha: float) -> bool | None:
    """None si pas de bootstrap ; sinon significatif au seuil du mode (10 % pour les étoiles)."""
    if boot is None or key not in boot.index:
        return None
    p = boot.loc[key, "p_value"]
    return bool(np.isfinite(p) and p < (0.10 if mode == "stars" else alpha))


def _edge_style(value: float, key, boot, alpha: float = 0.05, mode: str = "stars") -> str:
    sig = _significant(key, boot, mode, alpha)
    if mode == "colors" and sig is not None:
        return (f'color="{SIG_GREEN}", fontcolor="{SIG_GREEN}"' if sig
                else f'color="{SIG_RED}", fontcolor="{SIG_RED}", style=dashed')
    if sig is False:
        return f'color="{NONSIG}", fontcolor="#6B7889", style=dashed'
    c = SIG_POS if value >= 0 or sig is None else SIG_NEG
    return f'color="{c}", fontcolor="{c}"'


# ---------------------------------------------------------------- mise en page du diagramme
# Variables latentes placées par couches (exogènes à gauche) ou aux positions de l'éditeur ;
# les indicateurs de chaque variable vont du côté du bord le plus proche (gauche, droite, haut, bas),
# comme dans les diagrammes de PLS-SEM publiés. Unités : points Graphviz (y vers le haut).
_IND_GAP = 30.0   # écart entre deux indicateurs d'une même pile
_IND_DIST = 135.0  # distance variable latente -> indicateurs


def _ind_width(name: str) -> float:
    return 7.5 * len(str(name)) + 16.0


def _latent_positions(model: Model, positions: dict | None = None) -> dict[str, tuple[float, float]]:
    lvs = list(model.latents)
    if positions and all(lv in positions for lv in lvs):
        # éditeur : pixels, origine en haut à gauche -> points, y vers le haut ; un peu d'air pour les indicateurs
        return {lv: (1.6 * float(positions[lv][0]), -1.6 * float(positions[lv][1])) for lv in lvs}
    # couches : plus long chemin depuis les exogènes (composantes avant leur construit d'ordre supérieur)
    preds: dict[str, set] = {lv: set() for lv in lvs}
    for a, b in model.structural:
        if a in preds and b in preds:
            preds[b].add(a)
    for hoc, locs in getattr(model, "higher_order", {}).items():
        for loc in locs:
            if hoc in preds and loc in preds and hoc not in preds[loc]:
                preds[hoc].add(loc)
    layer: dict[str, int] = {}

    def depth(lv, seen=()):
        if lv in layer:
            return layer[lv]
        if lv in seen:  # cycle (non récursif normalement) : on coupe
            return 0
        layer[lv] = d = 1 + max((depth(p, seen + (lv,)) for p in preds[lv]), default=-1)
        return d

    for lv in lvs:
        depth(lv)
    cols: dict[int, list[str]] = {}
    for lv in lvs:  # ordre de déclaration conservé dans chaque couche
        cols.setdefault(layer[lv], []).append(lv)
    n_ind = max((len(model.measurement.get(lv, [])) for lv in lvs), default=1)
    v_gap = max(120.0, n_ind * _IND_GAP + 20.0)
    h_gap = 2 * _IND_DIST - 30.0
    pos = {}
    for c, members in cols.items():
        for i, lv in enumerate(members):
            pos[lv] = (c * h_gap, ((len(members) - 1) / 2 - i) * v_gap)
    return pos


def _indicator_sides(pos: dict[str, tuple[float, float]], taken: set[str] = frozenset()) -> dict[str, str]:
    """Côté (left/right/top/bottom) de chaque variable latente : celui du bord de la feuille le plus proche."""
    xs, ys = [p[0] for p in pos.values()], [p[1] for p in pos.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
    sides = {}
    for lv, (x, y) in pos.items():
        dl, dr = (x - x0) / w, (x1 - x) / w
        dt, db = ((y1 - y) / h, (y - y0) / h) if y1 - y0 > 1e-6 else (0.5, 0.5)
        if x1 - x0 > 1e-6 and min(dl, dr) < 0.25:  # sur une colonne extrême : à gauche ou à droite
            side = "left" if dl <= dr else "right"
        else:  # au milieu : vers le haut ou le bas (bas si égalité : les flèches longues passent au-dessus)
            side = "top" if dt < db else "bottom"
        if lv in taken and side == "bottom":
            side = "top"
        sides[lv] = side
    return sides


def _indicator_positions(center, side: str, names: list[str]) -> dict[str, tuple[float, float]]:
    cx, cy = center
    n = len(names)
    if side in ("left", "right"):
        x = cx - _IND_DIST if side == "left" else cx + _IND_DIST
        return {nm: (x, cy + ((n - 1) / 2 - i) * _IND_GAP) for i, nm in enumerate(names)}
    widths = [_ind_width(nm) for nm in names]
    total = sum(widths) + 16.0 * (n - 1)
    y = cy + 0.7 * _IND_DIST if side == "top" else cy - 0.7 * _IND_DIST
    out, x = {}, cx - total / 2
    for nm, wd in zip(names, widths):
        out[nm] = (x + wd / 2, y)
        x += wd + 16.0
    return out


def _pin(p: tuple[float, float]) -> str:
    return f'pos="{p[0] / 72:.3f},{p[1] / 72:.3f}!"'  # neato : pos en pouces


def model_to_dot(model: Model, res=None, show_indicators: bool = True, boot: pd.DataFrame | None = None,
                 label_mode: str = "stars", alpha: float = 0.05, positions: dict | None = None,
                 layout: str = "edges") -> str:
    """Diagramme Graphviz (DOT) du modèle, annoté des estimations si `res` est fourni.

    `boot` : tableau de bootstrap_statistics (index (type, nom)) ; les flèches portent alors
    `label_mode` : "stars" = étoiles (1 %, 5 %, 10 % à la fois), non significatif à 10 % en gris pointillé ;
    "colors" = coefficients seuls, vert si significatif au seuil `alpha`, rouge pointillé sinon ; "none" = coefficients seuls.
    `layout` : "edges" (défaut) = indicateurs placés vers le bord le plus proche de leur variable latente,
    variables latentes aux `positions` de l'éditeur si fournies, sinon par couches ; "flow" = disposition
    automatique de Graphviz (de gauche à droite).
    En mode "stars", les flèches sont colorées :
    bleu = positif significatif, rouge = négatif significatif, gris pointillé = non significatif (5 %)."""
    if label_mode == "none":  # coefficients seuls, sans couleur ni pointillés
        boot = None
    pinned = layout == "edges" and len(model.latents) > 0
    lv_pos = _latent_positions(model, positions) if pinned else {}
    ix_targets = {d for _, _, d in getattr(model, "interactions", [])}
    sides = _indicator_sides(lv_pos, ix_targets) if pinned else {}
    ind_pos: dict[str, tuple[float, float]] = {}
    for lv in lv_pos:
        ind_pos.update(_indicator_positions(lv_pos[lv], sides[lv], list(model.measurement.get(lv, []))))

    def at(node: str, p) -> str:
        return (", " + _pin(p)) if pinned and p is not None else ""

    head = ('  layout=neato; splines=true; overlap=true; outputorder=edgesfirst; bgcolor="transparent";' if pinned
            else '  rankdir=LR; splines=true; nodesep=0.25; ranksep=0.9; outputorder=edgesfirst; bgcolor="transparent";')
    lines = [
        "digraph G {",
        head,
        '  node [fontname="IBM Plex Sans", fontsize=12, fontcolor="#1C2B3A"];',
        '  edge [fontname="IBM Plex Sans", fontsize=10, color="#5B6878", fontcolor="#1C2B3A"];',
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
        name = html.escape(lv)
        label = f'<{name}>' if lv not in r2 else (
            f'<{name}<BR/><FONT POINT-SIZE="8" COLOR="#4A5A6C">R² = {num(r2[lv])}</FONT>>')
        extra = ", peripheries=2" if lv in getattr(model, "higher_order", {}) else ""
        lines.append(  # ellipse ajustée au texte : marge réduite, taille minimale faible
            f'  {_q("lv:" + lv)} [label={label}, shape=ellipse, style=filled, margin="0.10,0.05", '
            f'width=0.5, height=0.3, fillcolor="#E6EDF7", color="#2E5E9E", penwidth=1.3{extra}{at(lv, lv_pos.get(lv))}];'
        )
    if show_indicators:
        for lv in model.latents:
            for ind in model.measurement.get(lv, []):
                lines.append(f'  {_q("mv:" + ind)} [label={_q(ind)}, shape=box, style=filled, '
                             f'fillcolor="#FBF3E1", color="#B8862B", fontsize=9, margin="0.08,0.03", '
                             f'width=0.3, height=0.2, penwidth=0.8{at(ind, ind_pos.get(ind))}];')
                lab = ""
                if res is not None:
                    if model.modes[lv] == "A":
                        val, key = meas.outer_loadings[(lv, ind)], ("outer_loading", f"{lv} -> {ind}")
                    else:
                        val, key = meas.outer_weights[(lv, ind)], ("outer_weight", f"{ind} -> {lv}")
                    lab = f", label={_halo(_edge_label(val, key, boot, label_mode, alpha))}, fontsize=9"
                    sig = _significant(key, boot, label_mode, alpha)
                    if label_mode == "colors" and sig is not None:
                        lab += (f', color="{SIG_GREEN}", fontcolor="{SIG_GREEN}"' if sig
                                else f', style=dashed, color="{SIG_RED}", fontcolor="{SIG_RED}"')
                    elif sig is False:
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
                lab = f", label={_halo(_edge_label(val, key, boot, label_mode, alpha))}"
            a, b = (hoc, loc) if model.modes[hoc] == "A" else (loc, hoc)
            lines.append(f'  {_q("lv:" + a)} -> {_q("lv:" + b)} [color="#6B7889", fontcolor="#4A5A6C", '
                         f'style=dashed, arrowsize=0.7{lab}];')
    for s, d in model.structural:
        attrs = f'color="{SIG_POS}", fontcolor="{SIG_POS}"'
        if res is not None:
            v = res.path_coefficients.loc[s, d]
            key = ("direct", f"{s} -> {d}")
            attrs = (_edge_style(v, key, boot, alpha, label_mode) + f", label={_halo(_edge_label(v, key, boot, label_mode, alpha))}"
                     f", penwidth={1 + 3 * min(abs(v), 1):.2f}")
        lines.append(f'  {_q("lv:" + s)} -> {_q("lv:" + d)} [{attrs}];')
    for a, b, d in getattr(model, "interactions", []):
        name = f"{a}:{b}"
        attrs = 'color="#B8862B", fontcolor="#8a6d1f", style=dashed'
        if res is not None and name in res.path_coefficients.index:
            v = res.path_coefficients.loc[name, d]
            key = ("direct", f"{name} -> {d}")
            attrs = _edge_style(v, key, boot, alpha, label_mode) + f", label={_halo(_edge_label(v, key, boot, label_mode, alpha))}"
            if boot is None or key not in boot.index:
                attrs = 'color="#B8862B", fontcolor="#8a6d1f", style=dashed' + f", label={_halo(num(v))}"
        ix_p = None
        if pinned and d in lv_pos:  # sous la variable expliquée, légèrement à gauche
            ix_p = (lv_pos[d][0] - 0.45 * _IND_DIST, lv_pos[d][1] - 0.9 * _IND_DIST)
        lines.append(f'  {_q("ix:" + name)} [label={_q(a + " × " + b)}, shape=diamond, style=filled, '
                     f'fillcolor="#FBF3E1", color="#B8862B", fontsize=9{at(name, ix_p)}];')
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


def impute(x: pd.DataFrame, method: str, iterations: int = 10) -> pd.DataFrame:
    """Remplace les valeurs manquantes : "mean" (moyenne de la colonne) ou "regression" (imputation itérative :
    chaque colonne est prédite par régression linéaire sur les autres, jusqu'à stabilité)."""
    x = x.astype(float)
    miss = x.isna()
    filled = x.fillna(x.mean())
    if method == "mean" or not miss.any().any():
        return filled
    cols = [c for c in x.columns if miss[c].any()]
    for _ in range(iterations):
        prev = filled[cols].copy()
        for c in cols:
            others = [o for o in x.columns if o != c]
            obs = ~miss[c]
            a = np.column_stack([np.ones(obs.sum()), filled.loc[obs, others].to_numpy()])
            beta, *_ = np.linalg.lstsq(a, filled.loc[obs, c].to_numpy(), rcond=None)
            b = np.column_stack([np.ones((~obs).sum()), filled.loc[~obs, others].to_numpy()])
            pred = b @ beta
            lo, hi = x[c].min(), x[c].max()  # reste dans l'étendue observée de l'échelle
            filled.loc[~obs, c] = np.clip(pred, lo, hi)
        if np.nanmax(np.abs(filled[cols].to_numpy() - prev.to_numpy())) < 1e-6:
            break
    return filled


def prepare_data(df: pd.DataFrame, model: Model, keep: list[str] | None = None,
                 missing: str = "listwise") -> tuple[pd.DataFrame, list[str]]:
    """Sélectionne les indicateurs, convertit en numérique et traite les valeurs manquantes :
    "listwise" (lignes incomplètes supprimées), "mean" (moyenne) ou "regression" (imputation itérative).

    `keep` : colonnes supplémentaires conservées telles quelles (ex. variable de groupe)."""
    warnings = []
    keep = [c for c in (keep or []) if c not in model.indicators]
    absent = [c for c in model.indicators + keep if c not in df.columns]
    if absent:
        raise KeyError(T("Colonnes introuvables dans les données : {cols}", cols=", ".join(absent)))
    sub = df[model.indicators].apply(pd.to_numeric, errors="coerce")
    for c in keep:
        sub[c] = df[c]
    n0 = len(sub)
    if missing in ("mean", "regression"):
        n_miss = int(sub[model.indicators].isna().sum().sum())
        sub[model.indicators] = impute(sub[model.indicators], missing)
        if keep:
            sub = sub.dropna(subset=keep)
        if n_miss:
            warnings.append(T("{k} valeur(s) manquante(s) remplacée(s) ({how}) : {n} observations utilisées.",
                              k=n_miss, n=len(sub), how=T("moyenne") if missing == "mean" else T("régression")))
    sub = sub.dropna()
    if len(sub) < n0 and missing == "listwise":
        warnings.append(T("{k} ligne(s) avec valeurs manquantes ou non numériques supprimée(s) "
                          "(suppression par liste) : {n} observations utilisées.", k=n0 - len(sub), n=len(sub)))
    if len(sub) < 30:
        warnings.append(T("Moins de 30 observations : les résultats seront très instables."))
    return sub.reset_index(drop=True), warnings


# ---------------------------------------------------------------- variables de contrôle
def _slug(v) -> str:
    s = re.sub(r"[^0-9A-Za-z_]+", "_", str(v)).strip("_")
    return s or "x"


def _categories(series: pd.Series) -> list | None:
    """Modalités d'une colonne catégorielle (texte, 2 à 15 modalités), sinon None."""
    if pd.api.types.is_numeric_dtype(series):
        return None
    lv = sorted(series.dropna().astype(str).unique())
    return lv if 2 <= len(lv) <= 15 else None


def expand_controls(syntax: str, df: pd.DataFrame) -> tuple[str, list[str]]:
    """Dans les lignes structurelles, un nom qui n'est pas une variable latente mais une colonne des données
    devient une variable de contrôle : construit à un seul indicateur (colonne numérique) ou indicatrices
    0/1 (colonne catégorielle, la première modalité servant de référence)."""
    lines = syntax.splitlines()
    latents, indicators = set(), set()
    for ln in lines:
        body = ln.split("#", 1)[0]
        m = re.match(r"\s*([A-Za-z_][\w.]*)\s*(=~|<~)\s*(.+)", body)
        if m:
            latents.add(m.group(1))
            indicators.update(t.strip() for t in m.group(3).split("+"))
    taken = latents | set(map(str, df.columns))
    added: dict[str, list[str]] = {}  # colonne -> latentes créées
    new_meas: list[str] = []
    notes: list[str] = []

    def latent_for(col: str) -> list[str] | None:
        if col in added:
            return added[col]
        if col in latents or col not in df.columns or col in indicators:
            return None
        cats = _categories(df[col])
        if cats is None and not pd.api.types.is_numeric_dtype(df[col]):
            return None
        if cats is None:
            name = col.upper() if col.upper() not in taken else f"{col}_c"
            taken.add(name)
            new_meas.append(f"{name} =~ {col}")
            added[col] = [name]
            notes.append(T("{c} : variable de contrôle (construit {n} à un indicateur)", c=col, n=name))
        else:
            names = []
            for lvl in cats[1:]:
                ind = f"{col}_{_slug(lvl)}"
                name = ind.upper() if ind.upper() not in taken else f"{ind}_d"
                taken.add(name)
                new_meas.append(f"{name} =~ {ind}")
                names.append(name)
            added[col] = names
            notes.append(T("{c} : variable catégorielle, {k} indicatrice(s) (référence : {r})",
                           c=col, k=len(names), r=cats[0]))
        return added[col]

    out = []
    for ln in lines:
        body, _, comment = ln.partition("#")
        m = re.match(r"(\s*)([^~=<]+?)\s*~\s*([^~].*)$", body)
        if m and "=~" not in body and "<~" not in body:
            lhs = m.group(2).strip()
            rep = latent_for(lhs)
            if rep and len(rep) == 1:
                lhs = rep[0]
            terms = []
            for t in m.group(3).split("+"):
                t = t.strip()
                if ":" in t:
                    parts = [(latent_for(p.strip()) or [p.strip()]) for p in t.split(":")]
                    terms.append(":".join(p[0] for p in parts) if all(len(p) == 1 for p in parts) else t)
                else:
                    rep = latent_for(t)
                    terms.append(" + ".join(rep) if rep else t)
            ln = f"{m.group(1)}{lhs} ~ {' + '.join(terms)}" + (f"  #{comment}" if comment else "")
        out.append(ln)
    if not new_meas:
        return syntax, []
    # nouvelles lignes de mesure : avant la première ligne structurelle
    first_struct = next((i for i, ln in enumerate(out)
                         if "~" in ln.split("#", 1)[0] and "=~" not in ln and "<~" not in ln), len(out))
    while first_struct > 0 and out[first_struct - 1].strip().startswith("#"):  # garde le commentaire du bloc
        first_struct -= 1
    block = [T("# Variables de contrôle (un indicateur)")] + new_meas + [""]
    return "\n".join(out[:first_struct] + block + out[first_struct:]), notes


def add_dummy_columns(df: pd.DataFrame, syntax: str) -> pd.DataFrame:
    """Ajoute les indicatrices 0/1 (colonne_modalité) citées dans la syntaxe."""
    extra = {}
    for col in df.columns:
        cats = _categories(df[col])
        if not cats:
            continue
        s = df[col].astype("string")
        for lvl in cats:
            name = f"{col}_{_slug(lvl)}"
            if name not in df.columns and re.search(rf"(?<![\w.]){re.escape(name)}(?![\w.])", syntax):
                extra[name] = (s == str(lvl)).astype(float).where(s.notna())
    return df.assign(**extra) if extra else df
