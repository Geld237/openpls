"""Export du diagramme estimé en PNG (300 ppp) ou SVG, sans Graphviz : le DOT produit par model_to_dot
contient des positions fixées (pos="x,y!", en pouces) ; on le redessine avec matplotlib."""
from __future__ import annotations

import html
import re

_NODE = re.compile(r'^\s*"(?P<id>[^"]+)" \[(?P<attrs>.*)\];\s*$')
_EDGE = re.compile(r'^\s*"(?P<a>[^"]+)" -> "(?P<b>[^"]+)" \[(?P<attrs>.*)\];\s*$')


def _attr(attrs: str, name: str, default=None):
    m = re.search(rf'(?<![\w]){name}=("(?:[^"\\]|\\.)*"|[^,\]\s]+)', attrs)
    if not m:
        return default
    v = m.group(1)
    return v[1:-1].replace('\\"', '"') if v.startswith('"') else v


def _label(attrs: str) -> str:
    m = re.search(r"label=(<.*>)(?=, |\]|$)", attrs)
    if m:  # étiquette HTML : on garde le texte, <BR/> -> saut de ligne
        txt = re.sub(r"<BR\s*/?>", "\n", m.group(1)[1:-1])
        return html.unescape(re.sub(r"<[^>]+>", "", txt)).strip()
    v = _attr(attrs, "label")
    return (v or "").replace("\\n", "\n")


def parse_dot(dot: str) -> tuple[dict, list]:
    nodes, edges = {}, []
    for ln in dot.splitlines():
        e = _EDGE.match(ln)
        if e:
            a = e.group("attrs")
            edges.append({"a": e.group("a"), "b": e.group("b"), "label": _label(a),
                          "color": _attr(a, "color", "#5B6878"), "fontcolor": _attr(a, "fontcolor", "#1C2B3A"),
                          "dashed": _attr(a, "style") == "dashed", "width": float(_attr(a, "penwidth", 1.0))})
            continue
        n = _NODE.match(ln)
        if n and "pos=" in n.group("attrs"):
            a = n.group("attrs")
            x, y = (float(v) for v in _attr(a, "pos").rstrip("!").split(","))
            nodes[n.group("id")] = {"x": x, "y": y, "shape": _attr(a, "shape", "ellipse"), "label": _label(a),
                                    "fill": _attr(a, "fillcolor", "#FFFFFF"), "color": _attr(a, "color", "#1C2B3A"),
                                    "double": _attr(a, "peripheries") == "2"}
    return nodes, edges


def render(dot: str, fmt: str = "png") -> bytes:
    """Dessine le diagramme (positions fixées) et renvoie le fichier PNG ou SVG."""
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon

    nodes, edges = parse_dot(dot)
    if not nodes:
        raise ValueError("diagramme sans positions")
    xs = [n["x"] for n in nodes.values()]
    ys = [n["y"] for n in nodes.values()]
    w, h = max(xs) - min(xs) + 2.4, max(ys) - min(ys) + 1.6
    fig, ax = plt.subplots(figsize=(max(w, 4), max(h, 2.5)))
    ax.set_xlim(min(xs) - 1.2, max(xs) + 1.2)
    ax.set_ylim(min(ys) - 0.8, max(ys) + 0.8)
    ax.set_aspect("equal")
    ax.axis("off")
    patches = {}
    for nid, n in nodes.items():
        lines = n["label"].split("\n")
        width = max(0.55, 0.075 * max(len(s) for s in lines) + 0.25)
        if n["shape"] == "box":
            bw, bh = 0.07 * len(lines[0]) + 0.16, 0.24
            p = FancyBboxPatch((n["x"] - bw / 2, n["y"] - bh / 2), bw, bh, boxstyle="square,pad=0",
                               fc=n["fill"], ec=n["color"], lw=0.8, zorder=3)
            fs = 7.5
        elif n["shape"] == "diamond":
            dw, dh = width * 0.6, 0.3
            p = Polygon([(n["x"] - dw, n["y"]), (n["x"], n["y"] + dh), (n["x"] + dw, n["y"]), (n["x"], n["y"] - dh)],
                        closed=True, fc=n["fill"], ec=n["color"], lw=0.9, zorder=3)
            fs = 7.5
        else:
            eh = 0.42 if len(lines) == 1 else 0.58
            p = Ellipse((n["x"], n["y"]), width * 1.15, eh, fc=n["fill"], ec=n["color"], lw=1.3, zorder=3)
            if n["double"]:
                ax.add_patch(Ellipse((n["x"], n["y"]), width * 1.15 + 0.1, eh + 0.1, fc="none", ec=n["color"],
                                     lw=1.0, zorder=3))
            fs = 9
        ax.add_patch(p)
        patches[nid] = p
        ax.text(n["x"], n["y"], n["label"], ha="center", va="center", fontsize=fs, color="#1C2B3A", zorder=5,
                linespacing=1.15)
    for e in edges:
        if e["a"] not in nodes or e["b"] not in nodes:
            continue
        a, b = nodes[e["a"]], nodes[e["b"]]
        arr = FancyArrowPatch((a["x"], a["y"]), (b["x"], b["y"]), patchA=patches[e["a"]], patchB=patches[e["b"]],
                              arrowstyle="-|>", mutation_scale=9 + 2 * e["width"], color=e["color"],
                              lw=0.8 * e["width"], linestyle="--" if e["dashed"] else "-", zorder=2,
                              shrinkA=1, shrinkB=1)
        ax.add_patch(arr)
        if e["label"]:
            mx, my = (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2
            ax.text(mx, my, e["label"].replace("\n", " "), ha="center", va="center", fontsize=7.5,
                    color=e["fontcolor"], zorder=4,
                    bbox={"boxstyle": "square,pad=0.08", "fc": "white", "ec": "none"})
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=300 if fmt == "png" else None, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def python_script(syntax: str, file_name: str, fit_kwargs: dict, missing: str, n_boot: int, seed: int) -> str:
    """Script Python qui refait l'analyse avec la bibliothèque openpls (reproductibilité)."""
    kw = ", ".join(f"{k}={v!r}" for k, v in fit_kwargs.items())
    low = file_name.lower()
    if low.endswith((".xlsx", ".xls")):
        read = f"raw = pd.read_excel({file_name!r})"
    elif low.endswith((".sav", ".zsav")):
        read = f"raw = pd.read_spss({file_name!r})"
    elif low.endswith(".dta"):
        read = f"raw = pd.read_stata({file_name!r})"
    else:  # comme OpenPLS : séparateur détecté, virgule décimale reconnue
        read = (f"raw = pd.read_csv({file_name!r}, sep=None, engine=\"python\")\n"
                f"if raw.select_dtypes(\"number\").shape[1] == 0:\n"
                f"    raw = pd.read_csv({file_name!r}, sep=None, engine=\"python\", decimal=\",\")")
    return f'''"""Analyse OpenPLS reproductible (générée par OpenPLS).

Installation : pip install openpls   (ou depuis https://github.com/Geld237/openpls)
"""
import pandas as pd

from openpls import Model, bootstrap_statistics, fit, fornell_larcker, htmt, quality_criteria
from openpls.assessment import measurement_statistics
from openpls.effects import effect_statistics
from openpls.gui_helpers import add_dummy_columns, prepare_data

SYNTAX = {syntax.strip() + chr(10)!r}

# adapte le chemin du fichier
{read}
raw = add_dummy_columns(raw.rename(columns=str), SYNTAX)
model = Model.from_syntax(SYNTAX)
data, notes = prepare_data(raw, model, missing="{missing}")
print(*notes, sep="\\n")

res = fit(data, model{", " + kw if kw else ""})
print("Coefficients de chemin\\n", res.path_coefficients.round(3))
print("R²\\n", res.r_squared.round(3))
print("Qualité\\n", quality_criteria(res.measurement_result).round(3))
print("HTMT\\n", htmt(res.measurement_result).round(3))
print("Fornell-Larcker\\n", fornell_larcker(res.measurement_result).round(3))

boot = bootstrap_statistics(
    data, model, lambda r: pd.concat([effect_statistics(r), measurement_statistics(r)]),
    n_boot={n_boot}, seed={seed}{", " + kw if kw else ""})
print(boot.round(3))
'''
