import numpy as np
import pandas as pd
import pytest
from scipy import stats

from openpls import Model, fit
from openpls.endogeneity import gaussian_copula
from openpls.simulate import simulate


def endogenous_data(rho, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    u, e = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], n).T
    x = -np.log(1 - stats.norm.cdf(u))       # régresseur exponentiel (non normal)
    x = (x - x.mean()) / x.std()
    z = rng.normal(size=n)                    # second régresseur exogène normal
    y = 0.5 * x + 0.3 * z + e
    return pd.DataFrame({"x": x, "z": z, "y": y})


M = Model.from_syntax("X =~ x\nZ =~ z\nY =~ y\nY ~ X + Z")


def test_detects_and_corrects_endogeneity():
    d = endogenous_data(0.5)
    res = fit(d, M)
    out = gaussian_copula(res, "Y", n_boot=300)
    assert out["normality"].loc["X", "non normal (p<0,05)"]
    row = out["summary"].query("modèle == 'copules : X'").iloc[0]
    assert row["conclusion"] == "endogénéité"
    true_std = 0.5 / d["y"].std()
    # le chemin PLS est biaisé vers le haut, la copule le ramène près de la vraie valeur
    assert row["chemin PLS"] - true_std > 0.15
    assert abs(row["chemin corrigé"] - true_std) < 0.06


def test_no_false_alarm_without_endogeneity():
    d = endogenous_data(0.0, seed=1)
    out = gaussian_copula(fit(d, M), "Y", n_boot=300)
    row = out["summary"].query("modèle == 'copules : X'").iloc[0]
    assert row["conclusion"] == "pas d'endogénéité"
    assert len(out["summary"]) == 4  # {X}, {Z}, {X, Z} -> 1 + 1 + 2 lignes


def test_normal_regressor_is_not_interpretable():
    """Régresseur normal : la copule n'est pas identifiée, même si sa p-value est petite."""
    rng = np.random.default_rng(5)
    x, z = rng.normal(size=(2, 400))
    d = pd.DataFrame({"x": x, "z": z, "y": 0.5 * x + 0.3 * z + rng.normal(size=400)})
    out = gaussian_copula(fit(d, M), "Y", n_boot=100)
    assert (out["summary"]["conclusion"] == "non interprétable (régresseur normal)").all()


def test_on_simulated_model():
    d = simulate(300, seed=2)
    res = fit(d, Model.from_syntax("XI1 =~ xi1_1 + xi1_2 + xi1_3\nETA1 =~ eta1_1 + eta1_2\nETA1 ~ XI1"))
    out = gaussian_copula(res, "ETA1", n_boot=100)
    assert set(out["models"].index) == {"XI1", "copule(XI1)"}
    with pytest.raises(ValueError):
        gaussian_copula(res, "XI1")
