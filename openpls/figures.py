"""Figures de publication (matplotlib) : histogrammes, boîtes à moustaches, diagramme quantile-quantile,
carte des corrélations, éboulis des valeurs propres. Export PNG (300 ppp) ou SVG."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

INK, PATH, RULE, OCHRE, RED = "#1C2B3A", "#2E5E9E", "#D8DEE8", "#B8862B", "#B83A2E"


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 9, "axes.edgecolor": "#8A96A6", "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
        "axes.titlesize": 10, "axes.titleweight": "semibold", "figure.dpi": 100,
    })
    return plt


def to_bytes(fig, fmt: str = "png") -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=300 if fmt == "png" else None, bbox_inches="tight")
    return buf.getvalue()


def histogram(values: pd.Series, title: str, xlabel: str, density_label: str = "loi normale"):
    from scipy import stats

    plt = _plt()
    v = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    uniq = np.unique(v)
    bins = (np.append(uniq, uniq[-1] + 1) - 0.5) if len(uniq) <= 11 and np.allclose(uniq, np.round(uniq)) else "auto"
    ax.hist(v, bins=bins, color=PATH, alpha=0.85, edgecolor="white", density=True)
    if v.std() > 0:
        xs = np.linspace(v.min() - 0.5, v.max() + 0.5, 200)
        ax.plot(xs, stats.norm.pdf(xs, v.mean(), v.std(ddof=1)), color=OCHRE, lw=1.6, label=density_label)
        ax.legend(frameon=False, fontsize=8)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_yticks([])
    fig.tight_layout()
    return fig


def qq_plot(values: pd.Series, title: str, xlabel: str, ylabel: str):
    from scipy import stats

    plt = _plt()
    v = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    (osm, osr), (slope, inter, _) = stats.probplot(v, dist="norm")
    ax.scatter(osm, osr, s=8, color=PATH, alpha=0.6)
    ax.plot(osm, slope * osm + inter, color=OCHRE, lw=1.4)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def boxplots(df: pd.DataFrame, title: str):
    plt = _plt()
    data = [pd.to_numeric(df[c], errors="coerce").dropna().to_numpy(dtype=float) for c in df.columns]
    fig, ax = plt.subplots(figsize=(max(3.6, 0.55 * len(data) + 1.2), 3.0))
    bp = ax.boxplot(data, patch_artist=True, widths=0.55, medianprops={"color": INK, "lw": 1.4},
                    flierprops={"marker": "o", "markersize": 3, "markerfacecolor": RED, "markeredgecolor": RED})
    for b in bp["boxes"]:
        b.set(facecolor="#E6EDF7", edgecolor=PATH)
    ax.set_xticks(range(1, len(data) + 1), [str(c) for c in df.columns], rotation=45 if len(data) > 6 else 0,
                  ha="right" if len(data) > 6 else "center")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def correlation_heatmap(corr: pd.DataFrame, title: str, annotate: bool | None = None):
    plt = _plt()
    k = len(corr)
    size = min(max(3.6, 0.42 * k + 1.5), 11)
    fig, ax = plt.subplots(figsize=(size, size * 0.86))
    im = ax.imshow(corr.to_numpy(dtype=float), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(k), corr.columns, rotation=90, fontsize=7 if k > 15 else 8)
    ax.set_yticks(range(k), corr.index, fontsize=7 if k > 15 else 8)
    if annotate if annotate is not None else k <= 15:
        for i in range(k):
            for j in range(k):
                v = corr.iat[i, j]
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5,
                        color="white" if abs(v) > 0.6 else INK)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.colorbar(im, ax=ax, shrink=0.75)
    ax.set_title(title)
    fig.tight_layout()
    return fig


def scree_plot(eigenvalues, title: str, xlabel: str, ylabel: str):
    plt = _plt()
    ev = np.asarray(eigenvalues, dtype=float)
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    ax.plot(range(1, len(ev) + 1), ev, marker="o", color=PATH, lw=1.4, ms=4)
    ax.axhline(1, color=OCHRE, lw=1, ls="--")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig
