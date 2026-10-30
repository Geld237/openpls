import numpy as np
import pandas as pd
import pytest

from openpls import Model, fit, bootstrap_statistics, f_squared, quality_criteria
from openpls.moderation import simple_slopes, simple_slope_statistics
from openpls.simulate import simulate_moderation

SYNTAX = """
X =~ x_1 + x_2 + x_3
M =~ m_1 + m_2 + m_3
Y =~ y_1 + y_2 + y_3
Y ~ X + M + X:M
"""


def test_syntax_parses_interaction_and_roundtrips():
    m = Model.from_syntax(SYNTAX)
    assert m.interactions == [("X", "M", "Y")]
    assert set(m.structural) == {("X", "Y"), ("M", "Y")}
    assert Model.from_syntax(m.to_syntax()).interactions == m.interactions


def test_interaction_requires_main_effects():
    with pytest.raises(ValueError, match="effets simples"):
        Model.from_syntax("X =~ x_1\nM =~ m_1\nY =~ y_1\nY ~ X + X:M")


def test_single_indicator_equals_ols_with_product():
    """Sans erreur de mesure, le two-stage doit reproduire exactement la régression OLS standardisée."""
    rng = np.random.default_rng(3)
    n = 400
    x, mo = rng.normal(size=(2, n))
    y = 0.4 * x + 0.2 * mo + 0.3 * x * mo + rng.normal(0, 0.8, n)
    d = pd.DataFrame({"x": x, "m": mo, "y": y})
    res = fit(d, Model.from_syntax("X =~ x\nM =~ m\nY =~ y\nY ~ X + M + X:M"))
    z = lambda v: (v - v.mean()) / v.std(ddof=1)
    design = np.column_stack([z(x), z(mo), z(z(x) * z(mo))])
    beta = np.linalg.lstsq(design, z(y), rcond=None)[0]
    got = res.path_coefficients.loc[["X", "M", "X:M"], "Y"].to_numpy()
    np.testing.assert_allclose(got, beta, atol=1e-10)


@pytest.mark.parametrize("method", ["two_stage", "product_indicator", "orthogonal"])
def test_recovers_interaction(method):
    d = simulate_moderation(n=2000, loading=0.9, seed=1)
    res = fit(d, Model.from_syntax(SYNTAX), moderation=method)
    assert res.converged
    b = res.path_coefficients["Y"]
    # atténuation attendue (fiabilité ~0,92) : on vérifie signe et ordre de grandeur
    assert 0.17 < b["X:M"] < 0.30, b["X:M"]
    assert 0.30 < b["X"] < 0.45
    if method == "two_stage":
        assert res.stage1 is not None and "X:M" not in quality_criteria(res.measurement_result).index


def test_simple_slopes_and_bootstrap():
    d = simulate_moderation(n=500, seed=2)
    m = Model.from_syntax(SYNTAX)
    res = fit(d, m)
    ss = simple_slopes(res, "X", "M", "Y")
    b = res.path_coefficients["Y"]
    assert ss.loc[1.0, "pente"] == pytest.approx(b["X"] + b["X:M"])
    assert ss.loc[-1.0, "pente"] < ss.loc[1.0, "pente"]
    boot = bootstrap_statistics(d, m, simple_slope_statistics, n_boot=100, seed=0)
    assert boot.attrs["n_boot_failed"] == 0 and len(boot) == 3


def test_f2_of_interaction():
    d = simulate_moderation(n=600, seed=4)
    m = Model.from_syntax(SYNTAX)
    res = fit(d, m)
    f2 = f_squared(res, d)
    assert f2.loc["X:M -> Y", "f2"] > 0.02
    assert np.isfinite(f2["f2"]).all()


def test_product_indicator_rejects_formative():
    d = simulate_moderation(n=200)
    m = Model.from_syntax(SYNTAX.replace("X =~", "X <~"))
    with pytest.raises(ValueError, match="deux étapes"):
        fit(d, m, moderation="product_indicator")
    assert fit(d, m).converged  # le two-stage accepte le formatif
