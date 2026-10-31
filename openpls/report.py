"""Rapport Word (.docx) au format APA : paragraphe de méthode, tableaux du modèle de mesure et du modèle
structurel, diagramme. Le texte est un point de départ à relire et à adapter."""
from __future__ import annotations

import io
from datetime import date

import numpy as np
import pandas as pd

from . import __version__
from .gui_helpers import fmt_p, num
from .i18n import T


def _borders(table, header_rows: int = 1) -> None:
    """Style APA : filets horizontaux seulement (haut du tableau, sous l'en-tête, bas du tableau)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def set_border(cell, edge, val="single", sz=8):
        tc_pr = cell._tc.get_or_add_tcPr()
        borders = tc_pr.find(qn("w:tcBorders"))
        if borders is None:
            borders = OxmlElement("w:tcBorders")
            tc_pr.append(borders)
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), "000000")
        borders.append(el)

    rows = table.rows
    for c in rows[0].cells:
        set_border(c, "top")
    for c in rows[header_rows - 1].cells:
        set_border(c, "bottom")
    for c in rows[-1].cells:
        set_border(c, "bottom")


def _table(doc, number: int, title: str, df: pd.DataFrame, note: str | None = None, digits: int = 3) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    p = doc.add_paragraph()
    p.add_run(f"{T('Tableau')} {number}").bold = True
    p = doc.add_paragraph()
    p.add_run(title).italic = True
    df = df.copy()
    idx_names = [n or "" for n in df.index.names]
    df = df.reset_index()
    df.columns = idx_names + list(df.columns[len(idx_names):])
    t = doc.add_table(rows=1, cols=len(df.columns))
    for j, c in enumerate(df.columns):
        t.rows[0].cells[j].text = str(c)
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for j, (c, v) in enumerate(row.items()):
            if isinstance(v, (bool, np.bool_)):
                txt = T("oui") if v else T("non")
            elif isinstance(v, (int, np.integer)):
                txt = str(v)
            elif isinstance(v, (float, np.floating)):
                txt = "" if pd.isna(v) else (fmt_p(v) if str(c) == "p" else num(v, digits))
            else:
                txt = str(v)
            cells[j].text = txt
            if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_)):
                cells[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for row in t.rows:
        for c in row.cells:
            for par in c.paragraphs:
                for r in par.runs:
                    r.font.size = Pt(9)
    _borders(t)
    if note:
        p = doc.add_paragraph()
        p.add_run(T("Note.")).italic = True
        p.add_run(" " + note).font.size = Pt(9)
    doc.add_paragraph()


def build_report(info: dict, tables: dict, diagram_png: bytes | None = None) -> bytes:
    """`info` : n, algorithm, scheme, n_boot, ci_method, alpha, missing, moderation, hoc_method.
    `tables` : paths, loadings, quality, htmt, r2, f2 (DataFrames ; certains peuvent manquer)."""
    from docx import Document
    from docx.shared import Inches, Pt

    doc = Document()
    st_ = doc.styles["Normal"]
    st_.font.name = "Times New Roman"
    st_.font.size = Pt(12)
    doc.add_heading(T("Résultats de l'analyse PLS-SEM"), level=1)
    doc.add_paragraph(T("Rapport généré par OpenPLS {v} le {d}. Texte à relire et à adapter avant publication.",
                        v=__version__, d=date.today().isoformat())).runs[0].italic = True

    doc.add_heading(T("Méthode"), level=2)
    miss = {"listwise": T("suppression par liste"), "mean": T("remplacement par la moyenne"),
            "regression": T("imputation par régression")}.get(info.get("missing"), info.get("missing"))
    boot_txt = (T("La significativité a été évaluée par bootstrap ({b} tirages ; intervalles de confiance {m} à "
                  "{c} %).", b=info["n_boot"], m=info.get("ci_method", "percentile"),
                  c=num(100 * (1 - info.get("alpha", 0.05)), 0))
                if info.get("n_boot") else T("Le bootstrap n'a pas été réalisé : la significativité n'est pas "
                                             "rapportée."))
    doc.add_paragraph(
        T("Le modèle a été estimé par {algo} (OpenPLS {v} ; schéma de pondération {s}) sur n = {n} observations "
          "(valeurs manquantes : {m}). ", algo=info["algorithm"], v=__version__, s=info["scheme"], n=info["n"], m=miss)
        + boot_txt + " " + T("L'évaluation suit les recommandations de Hair et al. (2022) : modèle de mesure "
                             "(fiabilité, validité convergente et discriminante), puis modèle structurel."))

    n_tab = 1
    doc.add_heading(T("Modèle de mesure"), level=2)
    if "loadings" in tables:
        _table(doc, n_tab, T("Chargements et poids externes"), tables["loadings"],
               T("Chargements ≥ 0,708 recommandés (Hair et al., 2022)."))
        n_tab += 1
    if "quality" in tables:
        _table(doc, n_tab, T("Fiabilité et validité convergente"), tables["quality"],
               T("α, ρ_A et ρ_c ≥ 0,70 ; AVE ≥ 0,50."))
        n_tab += 1
    if "htmt" in tables:
        _table(doc, n_tab, T("Validité discriminante (HTMT)"), tables["htmt"],
               T("HTMT < 0,85 (Henseler et al., 2015)."))
        n_tab += 1

    doc.add_heading(T("Modèle structurel"), level=2)
    paths = tables.get("paths")
    if paths is not None:
        sentences = []
        for name, row in paths.iterrows():
            s = f"{name.replace(' -> ', ' → ')} : β = {num(row['coefficient'])}"
            if "t" in row and pd.notna(row.get("t")):
                s += f", t = {num(row['t'], 2)}, p {fmt_p(row['p']) if row['p'] < 0.001 else '= ' + fmt_p(row['p'])}"
            sentences.append(s)
        doc.add_paragraph(T("Coefficients de chemin : ") + " ; ".join(sentences) + ".")
        _table(doc, n_tab, T("Coefficients de chemin"), paths,
               T("*** p < 0,01 ; ** p < 0,05 ; * p < 0,10 ; ns non significatif.") if "t" in paths.columns else None)
        n_tab += 1
    if "r2" in tables:
        _table(doc, n_tab, T("Variance expliquée (R²)"), tables["r2"])
        n_tab += 1
    if "f2" in tables:
        _table(doc, n_tab, T("Taille d'effet f²"), tables["f2"],
               T("0,02 faible ; 0,15 moyen ; 0,35 fort (Cohen, 1988)."))
        n_tab += 1
    if diagram_png:
        p = doc.add_paragraph()
        p.add_run(T("Figure 1")).bold = True
        doc.add_paragraph().add_run(T("Modèle estimé")).italic = True
        doc.add_picture(io.BytesIO(diagram_png), width=Inches(6.3))

    doc.add_heading(T("Références"), level=2)
    for ref in (
        "Cohen, J. (1988). Statistical power analysis for the behavioral sciences (2nd ed.). Erlbaum.",
        "Hair, J. F., Hult, G. T. M., Ringle, C. M., & Sarstedt, M. (2022). A primer on partial least squares "
        "structural equation modeling (PLS-SEM) (3rd ed.). Sage.",
        "Henseler, J., Ringle, C. M., & Sarstedt, M. (2015). A new criterion for assessing discriminant validity in "
        "variance-based structural equation modeling. Journal of the Academy of Marketing Science, 43(1), 115-135.",
        f"OpenPLS contributors (2026). OpenPLS (version {__version__}) [Computer software]. "
        "https://github.com/Geld237/openpls",
    ):
        doc.add_paragraph(ref)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
