import numpy as np
import pandas as pd
import pytest

from openpls import Model
from openpls.predict import pls_predict, cvpat
from openpls.simulate import simulate

SYNTAX = """
XI1  =~ xi1_1 + xi1_2 + xi1_3
XI2  =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1
"""


def test_single_indicator_pls_equals_lm():
    """X -> Y avec un indicateur chacun : la prédiction PLS est exactement la régression simple."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=300)
    d = pd.DataFrame({"x": x, "y": 0.5 * x + rng.normal(size=300)})
    out = pls_predict(d, Model.from_syntax("X =~ x\nY =~ y\nY ~ X"), k=5, repetitions=2)["indicators"]
    assert out.loc["y", "PLS_RMSE"] == pytest.approx(out.loc["y", "LM_RMSE"], rel=1e-10)
    assert out.loc["y", "Q2_predict"] > 0.1


def test_plspredict_on_simulated_model():
    d = simulate(400, seed=5)
    out = pls_predict(d, Model.from_syntax(SYNTAX), k=10, repetitions=3)
    ind, lv = out["indicators"], out["latents"]
    assert list(ind.index) == ["eta1_1", "eta1_2", "eta1_3", "eta2_1", "eta2_2", "eta2_3"]
    assert (ind["Q2_predict"] > 0).all()
    # le modèle vrai est le modèle estimé : PLS doit faire au moins aussi bien que LM la plupart du temps
    assert ind["PLS < LM (RMSE)"].sum() >= 4
    assert lv.loc["ETA1", "Q2_predict"] > 0.2


def test_da_approach_and_errors():
    d = simulate(200, seed=1)
    m = Model.from_syntax(SYNTAX)
    da = pls_predict(d, m, k=5, repetitions=1, approach="DA")["latents"]
    ea = pls_predict(d, m, k=5, repetitions=1, approach="EA")["latents"]
    # ETA1 n'a que des exogènes comme prédécesseurs : EA et DA identiques
    assert da.loc["ETA1", "RMSE"] == pytest.approx(ea.loc["ETA1", "RMSE"])
    # ETA2 : DA utilise le score observé d'ETA1, donc prédit mieux
    assert da.loc["ETA2", "RMSE"] < ea.loc["ETA2", "RMSE"]
    with pytest.raises(ValueError):
        pls_predict(d, m, approach="XX")


def test_cvpat():
    d = simulate(400, seed=7)
    out = cvpat(d, Model.from_syntax(SYNTAX), k=10, repetitions=3)
    assert out.loc[("IA", "Global"), "PLS meilleur (p<0,05)"]
    assert out.loc[("IA", "Global"), "diff_perte"] < 0
    assert set(out.index.get_level_values(0)) == {"IA", "LM"}
