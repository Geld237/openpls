from pathlib import Path

import pandas as pd
import pytest

from openpls import Model, fit
from openpls.gui_helpers import guess_syntax, model_to_dot, prepare_data, to_excel
from openpls.simulate import simulate

APP = str(Path(__file__).parents[1] / "openpls" / "app.py")

SYNTAX = """
XI1  =~ xi1_1 + xi1_2 + xi1_3   # commentaire
XI2  <~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1
"""


def test_syntax_roundtrip():
    m = Model.from_syntax(SYNTAX)
    assert m.modes == {"XI1": "A", "XI2": "B", "ETA1": "A", "ETA2": "A"}
    assert set(m.structural) == {("XI1", "ETA1"), ("XI2", "ETA1"), ("ETA1", "ETA2")}
    m2 = Model.from_syntax(m.to_syntax())
    assert m2.measurement == m.measurement and set(m2.structural) == set(m.structural) and m2.modes == m.modes


@pytest.mark.parametrize("bad", ["XI1 xi1_1", "", "A =~ a1\nA =~ a2", "A =~ a1\nB ~ A"])
def test_syntax_errors(bad):
    with pytest.raises(ValueError):
        Model.from_syntax(bad)


def test_guess_syntax_groups_by_prefix():
    s = guess_syntax(["sat1", "sat2", "sat_3", "img-1", "img-2", "age"])
    m = Model.from_syntax(s)
    assert m.measurement == {"SAT": ["sat1", "sat2", "sat_3"], "IMG": ["img-1", "img-2"], "AGE": ["age"]}


def test_dot_and_excel():
    d = simulate(200)
    m = Model.from_syntax(SYNTAX)
    r = fit(d, m)
    dot = model_to_dot(m, r)
    assert dot.startswith("digraph") and "R² =" in dot and f"{r.path_coefficients.loc['ETA1', 'ETA2']:.3f}" in dot
    xls = to_excel({"Chemins": r.path_coefficients, "Chargements": r.outer_loadings.to_frame()})
    back = pd.read_excel(pd.io.common.BytesIO(xls), sheet_name=None)
    assert set(back) == {"Chemins", "Chargements"}


def test_prepare_data_listwise():
    d = simulate(100).astype(object)
    d.iloc[0, 0] = None
    d.iloc[1, 2] = "n/a"
    clean, warns = prepare_data(d, Model.from_syntax(SYNTAX))
    assert len(clean) == 98 and warns


# ------------------------------------------------------------------ application complète
def _app(auto_boot: bool = False):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["auto_boot"] = auto_boot  # bootstrap automatique coupé sauf test dédié (rapidité)
    return at


def _btn(at, label):
    return next(b for b in at.button if label in b.label)


def test_app_example_end_to_end():
    at = _app().run()
    assert not at.exception, at.exception
    _btn(at, "Estimer").click().run()
    assert not at.exception, at.exception
    # après l'estimation, l'application bascule sur l'onglet Résultats
    assert at.session_state["page"] == "Résultats"
    assert "Coefficients de chemin" in [s.value for s in at.subheader]
    at.number_input(key="n_boot").set_value(200).run()
    _btn(at, "bootstrap").click().run()
    assert not at.exception, at.exception
    subs = [s.value for s in at.subheader]
    assert "Analyse de médiation" in subs and "Effets indirects spécifiques" in subs


def test_app_syntax_error_is_reported():
    at = _app().run()
    at.text_area(key="syntax").set_value("XI1 =~ colonne_inexistante\nETA1 =~ eta1_1\nETA1 ~ XI1").run()
    assert not at.exception
    assert any("colonne_inexistante" in e.value for e in at.error)
    assert _btn(at, "Estimer").disabled
    at.text_area(key="syntax").set_value("XI1 =~ xi1_1\nETA ~ XI1").run()
    assert any("variable latente inconnue" in e.value for e in at.error)


def test_f2_with_isolated_latent_is_finite():
    import numpy as np
    from openpls import f_squared

    d = simulate(300)
    m = Model.from_syntax(SYNTAX)
    f2 = f_squared(fit(d, m), d)  # retirer XI2 -> ETA1 isole XI2
    assert np.isfinite(f2["f2"]).all() and (f2["f2"] > 0).all()


# ------------------------------------------------------------------ analyses avancées et modération
ADV_CASES = [
    ("Prédiction (PLSpredict, CVPAT)", {"pp_k": 5, "pp_r": 1}, "Lancer PLSpredict", "CVPAT"),
    ("Multigroupe (MGA, MICOM)", {"mga_np": 100, "mga_nb": 100}, "Lancer MGA", "Test omnibus (tous les groupes)"),
    ("Importance-performance (IPMA)", {}, None, "Niveau indicateur"),
    ("Conditions nécessaires (NCA)", {"nca_np": 100}, "Lancer la NCA", "Tableau des goulots"),
    ("Endogénéité (copules)", {"endo_nb": 100}, "Lancer le test", "Synthèse"),
    ("CB-SEM / CFA", {}, None, "Chargements standardisés"),
    ("Segmentation (FIMIX-PLS)", {"fx_st": 2}, "Lancer FIMIX", "Critères de choix du nombre de segments"),
]


def test_app_model_comparison_and_cta_message():
    at = _app().run()
    _btn(at, "Estimer").click().run()
    at.radio(key="adv_choice").set_value("Comparaison de modèles").run()
    at.text_area(key="cmp_syn_0").set_value(at.session_state["syntax"].replace("ETA2 ~ ETA1 + XI1", "ETA2 ~ ETA1")).run()
    _btn(at, "Comparer les modèles").click().run()
    assert not at.exception, at.exception
    tbl = next(df.value for df in at.dataframe if "BIC" in df.value.columns)
    assert len(tbl) == 2 and abs(tbl["poids BIC"].sum() - 1) < 1e-9
    at.radio(key="adv_choice").set_value("Tétrades (CTA-PLS)").run()
    _btn(at, "Lancer la CTA-PLS").click().run()
    assert not at.exception, at.exception
    assert any("4 indicateurs" in e.value for e in at.error)  # blocs de 3 indicateurs dans l'exemple


@pytest.mark.parametrize("choice,inputs,button,expected", ADV_CASES, ids=[c[0].split()[0] for c in ADV_CASES])
def test_app_advanced_analyses(choice, inputs, button, expected):
    at = _app().run()
    _btn(at, "Estimer").click().run()
    at.radio(key="adv_choice").set_value(choice).run()
    for k, v in inputs.items():
        at.number_input(key=k).set_value(v)
    if "fx_st" in inputs:
        at.slider(key="fx_s").set_value(3)
    at.run()
    if button:
        _btn(at, button).click().run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]
    assert expected in [s.value for s in at.subheader], [s.value for s in at.subheader]


def test_app_moderation_and_mga_detects_group_difference():
    at = _app().run()
    at.text_area(key="syntax").set_value(
        "XI1 =~ xi1_1 + xi1_2 + xi1_3\nXI2 =~ xi2_1 + xi2_2 + xi2_3\nETA1 =~ eta1_1 + eta1_2 + eta1_3\n"
        "ETA1 ~ XI1 + XI2 + XI1:XI2\n").run()
    _btn(at, "Estimer").click().run()
    assert not at.exception, at.exception
    assert "Modération : pentes simples" in [s.value for s in at.subheader]
    at.number_input(key="n_boot").set_value(100).run()
    _btn(at, "bootstrap").click().run()
    assert "Pentes simples (modération)" in [s.value for s in at.subheader]
    assert not at.exception, at.exception


def test_app_mga_two_groups():
    at = _app().run()
    _btn(at, "Estimer").click().run()
    at.radio(key="adv_choice").set_value("Multigroupe (MGA, MICOM)").run()
    at.multiselect(key="mga_lv").set_value(["A", "B"]).run()
    at.number_input(key="mga_np").set_value(100)
    at.number_input(key="mga_nb").set_value(100).run()
    _btn(at, "Lancer MGA").click().run()
    assert not at.exception, at.exception
    assert "Comparaison des chemins" in [s.value for s in at.subheader]


def test_app_higher_order_example():
    at = _app().run()
    at.sidebar.radio(key="source").set_value("example_hoc").run()
    assert "QUALITE =~ L1 + L2 + L3" in at.text_area(key="syntax").value
    for method in ("two_stage_disjoint", "repeated_indicators"):
        at.sidebar.selectbox(key="hoc_method").set_value(method).run()
        _btn(at, "Estimer").click().run()
        assert not at.exception, at.exception
        subs = [s.value for s in at.subheader]
        assert "Construits d'ordre supérieur" in subs
        paths = next(df.value for df in at.dataframe if df.value.index.name == "chemin")
        assert set(paths.index) == {"X -> QUALITE", "QUALITE -> Y"}, paths.index
    at.number_input(key="n_boot").set_value(100).run()
    _btn(at, "bootstrap").click().run()
    assert not at.exception, at.exception
    assert "Chargements des composantes (ordre supérieur)" in [s.value for s in at.subheader]
    at.radio(key="adv_choice").set_value("CB-SEM / CFA").run()
    assert "Chargements de second ordre" in [s.value for s in at.subheader]
    at.radio(key="adv_choice").set_value("Prédiction (PLSpredict, CVPAT)").run()
    assert any("ordre supérieur" in w.value for w in at.warning)


def test_desktop_mode_saves_exports_to_documents(tmp_path, monkeypatch):
    """Application de bureau : les exports sont enregistrés dans Documents/OpenPLS."""
    monkeypatch.setenv("OPENPLS_DESKTOP", "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    (tmp_path / "Documents").mkdir()
    at = _app().run()
    _btn(at, "Estimer").click().run()
    assert any(b.label == "Quitter OpenPLS" for b in at.sidebar.button)
    _btn(at, "Résultats (Excel)").click().run()
    assert not at.exception, at.exception
    files = list((tmp_path / "Documents" / "OpenPLS").glob("openpls_resultats_*.xlsx"))
    assert len(files) == 1
    sheets = pd.read_excel(files[0], sheet_name=None)
    assert "Chemins" in sheets and "Qualite" in sheets
    assert any("Enregistré" in s.value for s in at.sidebar.success)


def test_auto_bootstrap_shows_t_p_and_stars():
    """Après « Estimer », t, p, IC et étoiles apparaissent dans le tableau des chemins et le diagramme."""
    at = _app(auto_boot=True)
    at.session_state["n_boot"] = 200
    at.run()
    _btn(at, "Estimer").click().run()
    assert not at.exception, at.exception
    paths = next(df.value for df in at.dataframe if df.value.index.name == "chemin")
    assert {"t", "p", "sig."} <= set(paths.columns)
    assert paths.loc["ETA1 -> ETA2", "p"] < 0.001 and paths.loc["ETA1 -> ETA2", "sig."] == "***"
    assert paths.loc["XI1 -> ETA1", "t"] > 2
    dot = " ".join(g.proto.spec for g in at.get("graphviz_chart"))
    assert "***" in dot and "#2E5E9E" in dot
    loads = next(df.value for df in at.dataframe if "t (chargement)" in df.value.columns)
    assert (loads["sig. chargement"] == "***").all()
    # sans les étoiles : vert / rouge selon un seuil
    at.radio(key="sig_view").set_value("colors").run()
    dot = next(g.proto.spec for g in at.get("graphviz_chart") if "R²" in g.proto.spec)
    assert "*" not in dot and "#2F7D4F" in dot


def test_dot_marks_nonsignificant_paths():
    from openpls import bootstrap_statistics
    from openpls.assessment import measurement_statistics
    from openpls.effects import effect_statistics

    d = simulate(300, seed=2)          # XI1 -> ETA2 vaut 0 dans le vrai modèle
    m = Model.from_syntax(SYNTAX.replace("ETA2 ~ ETA1", "ETA2 ~ ETA1 + XI1"))
    r = fit(d, m)
    b = bootstrap_statistics(d, m, lambda x: pd.concat([effect_statistics(x), measurement_statistics(x)]),
                             n_boot=100)
    dot = model_to_dot(m, r, boot=b)
    line = next(l for l in dot.splitlines() if '"lv:XI1" -> "lv:ETA2"' in l)
    assert "style=dashed" in line and " ns" in line
    sig = next(l for l in dot.splitlines() if '"lv:ETA1" -> "lv:ETA2"' in l)
    assert "***" in sig and "#2E5E9E" in sig


def test_navigation_follows_the_workflow():
    """Estimer -> onglet Résultats ; changer de données -> retour à l'onglet Modèle."""
    at = _app().run()
    assert at.session_state["page"] == "Modèle"
    _btn(at, "Estimer").click().run()
    assert at.session_state["page"] == "Résultats"
    at.sidebar.radio(key="source").set_value("example_hoc").run()
    assert at.session_state["page"] == "Modèle"
    assert not at.exception, at.exception


def test_changing_threshold_keeps_bootstrap_and_stars():
    """Changer le seuil après l'estimation ne fait plus disparaître t, p et étoiles : seul l'IC change."""
    at = _app(auto_boot=True)
    at.session_state["n_boot"] = 100
    at.run()
    _btn(at, "Estimer").click().run()
    at.radio(key="sig_view").set_value("colors").run()
    for a, lo in ((0.01, "IC 0.5 %"), (0.10, "IC 5 %"), (0.05, "IC 2.5 %")):
        at.radio(key="alpha").set_value(a).run()
        assert not at.exception, at.exception
        paths = next(df.value for df in at.dataframe if df.value.index.name == "chemin")
        assert {"t", "p", "sig.", lo} <= set(paths.columns), (a, list(paths.columns))
        assert paths.loc["ETA1 -> ETA2", "sig."] == "***"
        dot = " ".join(g.proto.spec for g in at.get("graphviz_chart"))
        assert "#2F7D4F" in dot  # vert : significatif
    # le seuil choisi survit à un changement d'onglet et vaut pour la page Significativité
    at.radio(key="alpha").set_value(0.01).run()
    assert at.session_state["alpha_saved"] == 0.01
    assert any("IC à 99 %" in m.value for m in at.markdown)


def test_significance_modes_on_diagram():
    """Deux choix : étoiles (1, 5 et 10 % à la fois) ou couleurs selon un seuil (vert / rouge)."""
    from openpls import bootstrap_statistics
    from openpls.assessment import measurement_statistics
    from openpls.effects import effect_statistics

    d = simulate(300, seed=2)          # XI1 -> ETA2 vaut 0 dans le vrai modèle
    m = Model.from_syntax(SYNTAX.replace("ETA2 ~ ETA1", "ETA2 ~ ETA1 + XI1"))
    r = fit(d, m)
    b = bootstrap_statistics(d, m, lambda x: pd.concat([effect_statistics(x), measurement_statistics(x)]),
                             n_boot=100)
    col = model_to_dot(m, r, boot=b, label_mode="colors", alpha=0.05)
    sig = next(l for l in col.splitlines() if '"lv:ETA1" -> "lv:ETA2"' in l)
    ns = next(l for l in col.splitlines() if '"lv:XI1" -> "lv:ETA2"' in l)
    assert "#2F7D4F" in sig and "*" not in sig
    assert "#B83A2E" in ns and "style=dashed" in ns and "ns" not in ns


def test_star_convention_uses_three_thresholds():
    from openpls.gui_helpers import stars

    assert [stars(p) for p in (0.005, 0.03, 0.07, 0.2)] == ["***", "**", "*", "ns"]


def test_decimal_comma(monkeypatch):
    monkeypatch.setenv("OPENPLS_DECIMAL", ",")
    at = _app(auto_boot=True)
    at.session_state["n_boot"] = 100
    at.run()
    _btn(at, "Estimer").click().run()
    assert not at.exception, at.exception
    dot = " ".join(g.proto.spec for g in at.get("graphviz_chart"))
    assert "R² = 0," in dot and "R² = 0." not in dot
    assert any("p < 0,01" in c.value for c in at.caption)


def test_separator_follows_language():
    from openpls.settings import separator_for

    assert separator_for("fr_FR.UTF-8") == "," and separator_for("French_France") == ","
    assert separator_for("de_DE") == "," and separator_for("en_US") == "." and separator_for("English_United States") == "."
    assert separator_for(None) == "."


def test_indicators_point_to_nearest_edge():
    """Indicateurs du côté du bord le plus proche : exogènes à gauche, cible finale à droite, milieu en bas."""
    import re as _re

    m = Model.from_syntax(SYNTAX.replace("ETA2 ~ ETA1", "ETA2 ~ ETA1 + XI1"))
    dot = model_to_dot(m, fit(simulate(200, seed=3), m))
    assert "layout=neato" in dot
    pos = {n: tuple(map(float, xy.split(","))) for n, xy in _re.findall(r'"(\w+:[\w]+)" \[.*?pos="([-\d.]+,[-\d.]+)!"', dot)}
    assert pos["mv:xi1_1"][0] < pos["lv:XI1"][0]      # gauche
    assert pos["mv:eta2_1"][0] > pos["lv:ETA2"][0]    # droite
    assert pos["mv:eta1_1"][1] < pos["lv:ETA1"][1]    # au milieu : en bas
    # positions de l'éditeur : ETA1 tout en haut -> ses indicateurs au-dessus
    ed = {"XI1": (0, 200), "XI2": (0, 400), "ETA1": (300, 0), "ETA2": (600, 300)}
    dot = model_to_dot(m, positions=ed)
    pos = {n: tuple(map(float, xy.split(","))) for n, xy in _re.findall(r'"(\w+:[\w]+)" \[.*?pos="([-\d.]+,[-\d.]+)!"', dot)}
    assert pos["mv:eta1_1"][1] > pos["lv:ETA1"][1]


def test_edge_labels_have_opaque_background():
    """Chaque chiffre de flèche est posé sur un fond : une flèche qui le croise passe derrière."""
    m = Model.from_syntax(SYNTAX)
    dot = model_to_dot(m, fit(simulate(200, seed=3), m))
    edges = [l for l in dot.splitlines() if "->" in l and "label=" in l]
    assert edges and all('BGCOLOR="#F5F7FA"' in l for l in edges)
    assert "outputorder=edgesfirst" in dot


def test_every_interface_text_has_an_english_translation():
    import ast
    from pathlib import Path

    from openpls.i18n_en import EN

    root = Path(__file__).resolve().parent.parent / "openpls"
    missing = []
    for f in root.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "T" and node.args
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                if node.args[0].value not in EN:
                    missing.append(f"{f.name}: {node.args[0].value[:70]}")
    assert not missing, "\n".join(missing)


def test_app_runs_in_english(monkeypatch):
    monkeypatch.setenv("OPENPLS_LANG", "en")
    monkeypatch.setenv("OPENPLS_DECIMAL", ".")
    at = _app(auto_boot=True)
    at.session_state["n_boot"] = 100
    at.run()
    assert not at.exception, at.exception
    assert any("Estimate the model" in b.label for b in at.button)
    _btn(at, "Estimate").click().run()
    assert not at.exception, at.exception
    assert "Path coefficients" in [s.value for s in at.subheader]
    paths = next(df.value for df in at.dataframe if df.value.index.name == "path")
    assert {"std. error", "sig."} <= set(paths.columns)


def test_top_menu_and_update_check(monkeypatch):
    from openpls import menu

    assert menu.update_status("0.7.5", "0.8.0") == "newer"
    assert menu.update_status("0.8.0", "0.8.0") == "current"
    assert menu.update_status("0.10.0", "0.9.9") == "current"
    at = _app().run()
    labels = [b.label for b in at.button]
    assert {"À propos", "Mises à jour", "Paramètres"} <= set(labels)
    assert not at.exception, at.exception


def test_control_variables_and_quadratic_effect():
    import numpy as np

    from openpls.gui_helpers import add_dummy_columns, expand_controls

    d = simulate(300, seed=2)
    rng = np.random.default_rng(0)
    d["age"] = rng.integers(18, 70, 300)
    d["pays"] = rng.choice(["FR", "CM", "SN"], 300)
    syn = SYNTAX.replace("ETA1 ~ XI1 + XI2", "ETA1 ~ XI1 + XI2 + age + pays + XI1:XI1")
    s2, notes = expand_controls(syn, d)
    assert "AGE =~ age" in s2 and "PAYS_FR =~ pays_FR" in s2 and len(notes) == 2
    d2 = add_dummy_columns(d, s2)
    m = Model.from_syntax(s2)
    r = fit(d2[m.indicators], m)
    assert {"AGE", "PAYS_FR", "PAYS_SN", "XI1:XI1"} <= set(r.path_coefficients.index)
    assert expand_controls(s2, d2)[0] == s2  # idempotent


def test_bca_difference_and_moderated_mediation():
    at = _app(auto_boot=True)
    at.session_state["n_boot"] = 100
    at.run()
    at.text_area(key="syntax").set_value(SYNTAX.replace("ETA1 ~ XI1 + XI2", "ETA1 ~ XI1 + XI2 + XI1:XI2")).run()
    _btn(at, "Estimer").click().run()
    assert not at.exception, at.exception
    subs = [s.value for s in at.subheader]
    assert "Indice de médiation modérée (Hayes 2015)" in subs and "Comparer deux coefficients" in subs
    assert any("différence" in str(df.value.index.tolist()) for df in at.dataframe)
    at.radio(key="boot_ci").set_value("bca").run()
    assert not at.exception, at.exception
    assert any("Intervalles BCa." in c.value for c in at.caption)


def test_exports_report_project_script_and_diagram(tmp_path):
    import io
    import zipfile

    from docx import Document

    from openpls.diagram_export import render
    from openpls.project import load_project

    at = _app(auto_boot=True)
    at.session_state["n_boot"] = 100
    at.run()
    _btn(at, "Estimer").click().run()
    assert not at.exception, at.exception
    rep = at.session_state["_report"][1]
    doc = Document(io.BytesIO(rep))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Coefficients de chemin" in text and len(doc.tables) >= 4 and doc.inline_shapes
    png = at.session_state["_diagram_cache"][1]
    assert png[:4] == b"\x89PNG"
    # projet : aller-retour
    from openpls.project import save_project

    raw = simulate(50, seed=1)
    blob = save_project(raw, "x.csv", SYNTAX, {"XI1": (10, 20)}, {"algo": "PLS", "n_boot": 300})
    proj = load_project(blob)
    assert proj["syntax"] == SYNTAX and proj["settings"]["n_boot"] == 300 and proj["editor_pos"]["XI1"] == (10, 20)
    assert proj["data"].shape == raw.shape
    assert zipfile.ZipFile(io.BytesIO(blob)).namelist() == ["project.json", "data.csv"]
    # script Python : il s'exécute
    from openpls.diagram_export import python_script

    raw.to_csv(tmp_path / "d.csv", index=False)
    code = python_script(SYNTAX, str(tmp_path / "d.csv"), {"scheme": "path"}, "listwise", 50, 1)
    exec(compile(code, "script", "exec"), {"__name__": "__main__"})


def test_project_with_results_autosave_and_recent(tmp_path, monkeypatch):
    from openpls import project as pj

    monkeypatch.setenv("OPENPLS_HOME", str(tmp_path))
    at = _app(auto_boot=True)
    at.session_state["n_boot"] = 100
    at.run()
    _btn(at, "Estimer").click().run()
    at.radio(key="adv_choice").set_value("Conditions nécessaires (NCA)").run()
    at.number_input(key="nca_np").set_value(100).run()
    _btn(at, "Lancer la NCA").click().run()
    assert not at.exception, at.exception
    blob = at.session_state["_proj_blob"][1]
    proj = pj.load_project(blob)
    assert proj["results"]["fitted"] and "boot" in proj["results"] and "nca" in proj["results"]["adv"]
    assert (tmp_path / "autosave.openpls").is_file()  # sauvegarde automatique (résultats calculés)

    # nouvelle session : la reprise est proposée, puis restaure résultats, bootstrap et NCA sans recalcul
    at2 = _app().run()
    assert any("Reprendre le travail en cours" in m.value for m in at2.markdown)
    _btn(at2, "Reprendre").click().run()
    assert not at2.exception, at2.exception
    assert at2.session_state["source"] == "project"
    pages = ["Modèle", "Analyses préliminaires", "Résultats", "Significativité", "Analyses avancées", "Aide"]
    assert at2.session_state["page"] == pages[proj["results"]["page"]]  # onglet où l'on s'était arrêté
    assert "Coefficients de chemin" in [s.value for s in at2.subheader]
    paths = next(df.value for df in at2.dataframe if df.value.index.name == "chemin")
    assert "t" in paths.columns  # bootstrap restauré
    assert any(n == "nca" for n in at2.session_state["adv"])

    # projets récents
    pj.remember_recent("a.openpls", blob, {"name": "a.openpls", "date": "2026-10-31 10:00", "rows": 450})
    assert pj.list_recent()[0]["name"] == "a.openpls" and pj.read_recent(pj.list_recent()[0]) == blob
    pj.clear_history()
    assert not pj.list_recent() and pj.read_autosave() is None


def test_resume_offer_does_not_block_autosave(tmp_path, monkeypatch):
    """Audit : travailler sans répondre au bandeau ne doit pas empêcher la sauvegarde automatique."""
    from openpls import project as pj

    monkeypatch.setenv("OPENPLS_HOME", str(tmp_path))
    pj.write_autosave(b"ancien", {"name": "ancien.openpls", "date": "2026-01-01 00:00", "rows": 1})
    at = _app().run()
    assert any("Reprendre le travail en cours" in m.value for m in at.markdown)
    _btn(at, "Estimer").click().run()
    assert not any("Reprendre le travail en cours" in m.value for m in at.markdown)
    assert pj.read_autosave()[1]["rows"] == 450  # la sauvegarde a repris


def test_results_diagram_layout_spacing_and_export():
    from openpls.diagram_component import diagram_data, display_positions, merge_layout
    from openpls.diagram_export import render_layout

    m = Model.from_syntax(SYNTAX)
    dot = model_to_dot(m, fit(simulate(200, seed=3), m))
    nodes, edges, auto = diagram_data(dot, m)
    assert set(auto["lv"]) == {"lv:XI1", "lv:XI2", "lv:ETA1", "lv:ETA2"}
    assert {n["owner"] for n in nodes if n["kind"] == "mv"} <= set(auto["lv"])
    p1 = display_positions(nodes, auto, 1.0)
    p2 = display_positions(nodes, auto, 0.5)
    # espacement : latentes rapprochées, indicateurs à la même distance de leur latente
    d = lambda P, a, b: ((P[a][0] - P[b][0]) ** 2 + (P[a][1] - P[b][1]) ** 2) ** 0.5  # noqa: E731
    assert abs(d(p2, "lv:XI1", "lv:ETA2") - 0.5 * d(p1, "lv:XI1", "lv:ETA2")) < 1e-9
    assert abs(d(p2, "lv:XI1", "mv:xi1_1") - d(p1, "lv:XI1", "mv:xi1_1")) < 1e-9
    # disposition de l'utilisateur : déplacer une latente déplace ses indicateurs
    saved = {"lv": {**auto["lv"], "lv:ETA1": [auto["lv"]["lv:ETA1"][0], auto["lv"]["lv:ETA1"][1] + 100]}, "off": {}}
    p3 = display_positions(nodes, merge_layout(auto, saved), 1.0)
    assert abs(p3["mv:eta1_1"][1] - p1["mv:eta1_1"][1] - 100) < 1e-9
    png = render_layout(nodes, edges, p3, "png")
    assert png[:4] == b"\x89PNG"
    at = _app().run()
    _btn(at, "Estimer").click().run()
    assert not at.exception, at.exception
    assert at.session_state["_diagram_cache"][1][:4] == b"\x89PNG"
