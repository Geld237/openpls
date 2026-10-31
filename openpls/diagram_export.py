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


def _node_size(n: dict) -> tuple[float, float]:
    """Demi-largeur et demi-hauteur, comme dans le composant interactif (pixels = points)."""
    lines = n["label"].split("\n")
    size = 13 if n["kind"] == "lv" else 11.5
    w = max(len(s) * size * 0.56 for s in lines)
    if n["kind"] == "lv":
        return max(30.0, w / 2 + 16), (24.0 if len(lines) > 1 else 18.0)
    if n["kind"] == "ix":
        return max(34.0, w / 2 + 18), 20.0
    return w / 2 + 8, 11.0


def _clip(p, q, n, rx, ry):
    import math

    dx, dy = q[0] - p[0], q[1] - p[1]
    if n["kind"] == "mv":
        t = min(rx / abs(dx or 1e-9), ry / abs(dy or 1e-9))
    else:
        t = 1 / math.sqrt((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) + 1e-12)
    t = min(t, 0.45)
    return p[0] + dx * t, p[1] + dy * t


def render_layout(nodes: list, edges: list, P: dict, fmt: str = "png", paper: str = "white") -> bytes:
    """Dessine le diagramme aux positions `P` (pixels, y vers le bas) ; 1 pixel = 1 point, comme à l'écran."""
    import io

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse, FancyArrowPatch, Polygon, Rectangle

    sizes = {n["id"]: _node_size(n) for n in nodes}
    xs0 = min(P[n["id"]][0] - sizes[n["id"]][0] for n in nodes) - 24
    xs1 = max(P[n["id"]][0] + sizes[n["id"]][0] for n in nodes) + 24
    ys0 = min(P[n["id"]][1] - sizes[n["id"]][1] for n in nodes) - 24
    ys1 = max(P[n["id"]][1] + sizes[n["id"]][1] for n in nodes) + 24
    fig = plt.figure(figsize=((xs1 - xs0) / 72, (ys1 - ys0) / 72))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(xs0, xs1)
    ax.set_ylim(ys1, ys0)  # y vers le bas, comme à l'écran
    ax.axis("off")
    byid = {n["id"]: n for n in nodes}
    for e in edges:
        if e["a"] not in P or e["b"] not in P:
            continue
        na, nb = byid[e["a"]], byid[e["b"]]
        pa = _clip(P[e["a"]], P[e["b"]], na, *sizes[e["a"]])
        pb = _clip(P[e["b"]], P[e["a"]], nb, *sizes[e["b"]])
        ax.add_patch(FancyArrowPatch(pa, pb, arrowstyle="-|>", mutation_scale=9, color=e["color"],
                                     lw=0.9 * e["width"], linestyle=(0, (5, 4)) if e["dashed"] else "-",
                                     shrinkA=0, shrinkB=0, zorder=1))
        if e["label"]:
            fs = 10.5 if e.get("small") else 11.5
            ax.text((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, e["label"].replace("\n", " "), ha="center",
                    va="center", fontsize=fs, color=e["fontcolor"], zorder=2,
                    bbox={"boxstyle": "square,pad=0.1", "fc": paper, "ec": "none"})
    for n in nodes:
        (x, y), (rx, ry) = P[n["id"]], sizes[n["id"]]
        if n["kind"] == "mv":
            ax.add_patch(Rectangle((x - rx, y - ry), 2 * rx, 2 * ry, fc=n["fill"], ec=n["stroke"], lw=1, zorder=3))
        elif n["kind"] == "ix":
            ax.add_patch(Polygon([(x - rx, y), (x, y - ry), (x + rx, y), (x, y + ry)], closed=True, fc=n["fill"],
                                 ec=n["stroke"], lw=1, zorder=3))
        else:
            if n.get("double"):
                ax.add_patch(Ellipse((x, y), 2 * rx + 8, 2 * ry + 8, fc="none", ec=n["stroke"], lw=1, zorder=3))
            ax.add_patch(Ellipse((x, y), 2 * rx, 2 * ry, fc=n["fill"], ec=n["stroke"], lw=1.5, zorder=3))
        lines = n["label"].split("\n")
        for i, ln in enumerate(lines):
            fs = (13 if i == 0 else 11) if n["kind"] == "lv" else 11.5
            ax.text(x, y + (i - (len(lines) - 1) / 2) * 15, ln, ha="center", va="center", fontsize=fs, zorder=4,
                    fontweight="semibold" if n["kind"] == "lv" and i == 0 else "normal",
                    color="#1C2B3A" if i == 0 else "#4A5A6C")
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=300 if fmt == "png" else None, facecolor=paper)
    plt.close(fig)
    return buf.getvalue()


def render(dot: str, fmt: str = "png") -> bytes:
    """Export du DOT à positions fixées (disposition automatique)."""
    nodes_raw, edges = parse_dot(dot)
    if not nodes_raw:
        raise ValueError("diagramme sans positions")
    nodes = [{"id": k, "kind": k.split(":", 1)[0] if k.split(":", 1)[0] in ("lv", "mv", "ix") else "mv",
              "label": n["label"], "fill": n["fill"], "stroke": n["color"], "double": n["double"]}
             for k, n in nodes_raw.items()]
    for e in edges:
        e["small"] = e["a"].startswith("mv:") or e["b"].startswith("mv:")
    P = {k: (72 * n["x"], -72 * n["y"]) for k, n in nodes_raw.items()}
    return render_layout(nodes, edges, P, fmt)


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
