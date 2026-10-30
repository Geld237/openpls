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
def _app():
    from streamlit.testing.v1 import AppTest

    return AppTest.from_file(APP, default_timeout=120)


def _btn(at, label):
    return next(b for b in at.button if label in b.label)


def test_app_example_end_to_end():
    at = _app().run()
    assert not at.exception, at.exception
    _btn(at, "Estimer").click().run()
    assert not at.exception, at.exception
    assert any("Résultats" in t.value for t in at.title)
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
    at.sidebar.radio(key="source").set_value("Exemple de second ordre").run()
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
