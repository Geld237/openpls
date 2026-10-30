import numpy as np
import pandas as pd
import pytest

from openpls import Model, fit, bootstrap_statistics, f_squared, quality_criteria
from openpls.effects import effect_statistics, specific_indirect_effects
from openpls.higher_order import higher_order_measurement, higher_order_statistics, METHODS
from openpls.simulate import simulate_higher_order

SYNTAX = """
X   =~ x_1 + x_2 + x_3
L1  =~ l1_1 + l1_2 + l1_3
L2  =~ l2_1 + l2_2 + l2_3
L3  =~ l3_1 + l3_2 + l3_3
Y   =~ y_1 + y_2 + y_3
HOC =~ L1 + L2 + L3
HOC ~ X
Y ~ HOC
"""


def test_syntax():
    m = Model.from_syntax(SYNTAX)
    assert m.higher_order == {"HOC": ["L1", "L2", "L3"]} and m.modes["HOC"] == "A"
    assert "HOC" in m.latents and "HOC" not in m.measurement
    assert m.indicators == [f"{p}_{k}" for p in ("x", "l1", "l2", "l3", "y") for k in (1, 2, 3)]
    m2 = Model.from_syntax(m.to_syntax())
    assert m2.higher_order == m.higher_order and set(m2.structural) == set(m.structural)


@pytest.mark.parametrize("bad,msg", [
    ("A =~ a1\nB =~ b1\nH =~ A + b2", "mélange"),
    ("A =~ a1\nH =~ A", "au moins 2"),
    ("A =~ a1\nB =~ b1\nH =~ A + B\nC =~ c1\nB ~ C", "composante"),
    ("A =~ a1\nB =~ b1\nC =~ c1\nH =~ A + B\nG =~ H + C", "troisième ordre"),
    ("A =~ a1\nB =~ b1\nC =~ c1\nH =~ A + B\nG =~ B + C", "deux construits"),
])
def test_syntax_errors(bad, msg):
    with pytest.raises(ValueError, match=msg):
        Model.from_syntax(bad)


def test_plsc_two_stage_recovers_truth():
    d = simulate_higher_order(5000, seed=1)
    r = fit(d, Model.from_syntax(SYNTAX), consistent=True)
    assert r.hoc_method == "two_stage_disjoint" and r.stage1 is not None
    assert r.path_coefficients.loc["X", "HOC"] == pytest.approx(0.5, abs=0.04)
    assert r.path_coefficients.loc["HOC", "Y"] == pytest.approx(0.6, abs=0.04)


@pytest.mark.parametrize("method", METHODS)
def test_methods_agree_and_hoc_assessment(method):
    d = simulate_higher_order(1000, seed=2)
    r = fit(d, Model.from_syntax(SYNTAX), hoc_method=method)
    assert r.converged
    assert 0.33 < r.path_coefficients.loc["X", "HOC"] < 0.45   # atténuation PLS attendue
    hm = higher_order_measurement(r)
    lam = hm["components"]["chargement"].to_numpy()
    assert (lam > 0.7).all() and lam[0] > lam[2]            # ordre des vrais chargements 0,8 > 0,7
    q = hm["quality"].loc["HOC"]
    assert q["AVE"] > 0.5 and q["rho_c"] > 0.7
    # le HOC n'apparaît pas dans les critères des construits d'ordre 1
    assert "HOC" not in quality_criteria(r.measurement_result).index
    # les relations HOC -> composantes ne sont pas des effets structurels
    stats = effect_statistics(r)
    assert not any("L1" in k for k in stats.index.get_level_values(1))
    assert list(specific_indirect_effects(r).index) == ["X -> HOC -> Y"]


def test_two_stage_equals_manual_second_stage():
    d = simulate_higher_order(400, seed=3)
    m = Model.from_syntax(SYNTAX)
    r = fit(d, m)
    manual = d[["x_1", "x_2", "x_3", "y_1", "y_2", "y_3"]].copy()
    for loc in ("L1", "L2", "L3"):
        manual[f"{loc}__score"] = r.stage1.scores[loc]
    m2 = Model.from_syntax("X =~ x_1 + x_2 + x_3\nY =~ y_1 + y_2 + y_3\n"
                           "HOC =~ L1__score + L2__score + L3__score\nHOC ~ X\nY ~ HOC")
    np.testing.assert_allclose(fit(manual, m2).path_coefficients.loc[["X", "HOC"], ["HOC", "Y"]],
                               r.path_coefficients.loc[["X", "HOC"], ["HOC", "Y"]], atol=1e-10)


def test_formative_hoc():
    d = simulate_higher_order(800, seed=4)
    for method in METHODS:
        r = fit(d, Model.from_syntax(SYNTAX.replace("HOC =~", "HOC <~")), hoc_method=method)
        hm = higher_order_measurement(r)
        assert hm["quality"].loc["HOC", "type"] == "formatif"
        assert np.isfinite(hm["components"]["poids"]).all() and (hm["components"]["VIF"] < 5).all()


def test_f2_and_bootstrap():
    d = simulate_higher_order(300, seed=5)
    m = Model.from_syntax(SYNTAX)
    for method in METHODS:
        r = fit(d, m, hoc_method=method)
        f2 = f_squared(r, d)
        assert set(f2.index) == {"X -> HOC", "HOC -> Y"} and np.isfinite(f2["f2"]).all()
    boot = bootstrap_statistics(d, m, lambda r: pd.concat([effect_statistics(r), higher_order_statistics(r)]),
                                n_boot=60, seed=0)
    assert boot.attrs["n_boot_failed"] == 0
    assert ("hoc_loading", "HOC -> L1") in boot.index


@pytest.mark.parametrize("method", METHODS)
def test_other_analyses_accept_hoc_models(method):
    from openpls.endogeneity import gaussian_copula
    from openpls.fimix import fimix
    from openpls.ipma import ipma
    from openpls.mga import mga
    from openpls.nca import nca
    from openpls.predict import pls_predict

    d = simulate_higher_order(300, seed=6)
    m = Model.from_syntax(SYNTAX)
    r = fit(d, m, hoc_method=method)
    assert list(nca(r, "Y", n_perm=20)["effects"].index) == ["HOC"]
    assert set(gaussian_copula(r, "HOC", n_boot=20)["normality"].index) == {"X"}
    paths = fimix(r, segments=[1, 2], starts=2)["solutions"][1]["paths"].index
    assert set(paths) == {"X -> HOC", "HOC -> Y"}
    out = mga(d, m, np.repeat(["a", "b"], 150), n_perm=30, n_boot=20, hoc_method=method)
    assert set(out["comparison"].index) == {"X -> HOC", "HOC -> Y"}
    assert "HOC" not in out["micom_step2"].index and "L1" in out["micom_step2"].index
    with pytest.raises(ValueError, match="ordre supérieur"):
        pls_predict(d, m)
    with pytest.raises(ValueError, match="ordre supérieur"):
        ipma(r, d, "Y")
