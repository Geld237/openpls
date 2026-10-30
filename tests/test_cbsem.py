import numpy as np
import pytest

from openpls import Model
from openpls.cbsem import fit_cbsem
from openpls.simulate import simulate

MEAS = """
XI1  =~ xi1_1 + xi1_2 + xi1_3
XI2  =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3
"""
FULL = MEAS + "ETA1 ~ XI1 + XI2\nETA2 ~ ETA1 + XI1\n"


def test_recovers_true_parameters_and_fits():
    d = simulate(3000, seed=0, direct=0.15)
    r = fit_cbsem(d, Model.from_syntax(FULL))
    assert r.converged
    pc = r.path_coefficients
    for (s, t), true in {("XI1", "ETA1"): 0.5, ("XI2", "ETA1"): 0.3, ("ETA1", "ETA2"): 0.6, ("XI1", "ETA2"): 0.15}.items():
        assert pc.loc[s, t] == pytest.approx(true, abs=0.04), (s, t)
    assert np.allclose(r.loadings, 0.8, atol=0.04)
    assert r.latent_correlations.loc["XI1", "XI2"] == pytest.approx(0.3, abs=0.05)
    f = r.fit_indices
    assert f["ddl"] == 78 - 29 and f["CFI"] > 0.99 and f["RMSEA"] < 0.03 and f["SRMR"] < 0.03


def test_misspecification_detected():
    d = simulate(1000, seed=1, direct=0.4)
    good = fit_cbsem(d, Model.from_syntax(FULL)).fit_indices
    bad = fit_cbsem(d, Model.from_syntax(MEAS + "ETA1 ~ XI1 + XI2\nETA2 ~ ETA1\n")).fit_indices
    assert bad["ddl"] == good["ddl"] + 1
    assert bad["chi2"] - good["chi2"] > 30
    assert bad["p_value"] < 0.001 and bad["CFI"] < good["CFI"]


def test_cfa_correlates_all_latents():
    d = simulate(800, seed=2)
    r = fit_cbsem(d, Model.from_syntax(FULL), cfa=True)
    assert r.fit_indices["ddl"] == 78 - (8 + 10 + 12)  # 8 chargements, 4 var + 6 cov latentes, 12 résidus
    assert r.latent_correlations.loc["XI1", "ETA1"] == pytest.approx(0.5 + 0.3 * 0.3, abs=0.07)
    assert (r.path_coefficients == 0).all().all()


def test_standard_errors_close_to_semopy_reference():
    """Valeurs de référence obtenues avec semopy 2.3.11 (obj='MLW') sur simulate(500, seed=0, direct=0.15)."""
    d = simulate(500, seed=0, direct=0.15)
    r = fit_cbsem(d, Model.from_syntax(FULL))
    assert r.fit_indices["chi2"] == pytest.approx(44.258544, abs=1e-3)
    est = r.estimates
    assert est.loc["ETA2 ~ ETA1", "estimate"] == pytest.approx(0.6200, abs=1e-3)
    assert est.loc["ETA2 ~ ETA1", "std_error"] == pytest.approx(0.0618, abs=1e-3)


def test_rejects_formative():
    with pytest.raises(ValueError, match="réflectifs"):
        fit_cbsem(simulate(100), Model.from_syntax(FULL.replace("XI1  =~", "XI1  <~")))


HOC_SYNTAX = """X =~ x_1 + x_2 + x_3
L1 =~ l1_1 + l1_2 + l1_3
L2 =~ l2_1 + l2_2 + l2_3
L3 =~ l3_1 + l3_2 + l3_3
Y =~ y_1 + y_2 + y_3
HOC =~ L1 + L2 + L3
HOC ~ X
Y ~ HOC"""


def test_second_order_matches_semopy_reference():
    """Valeurs de référence semopy 2.3.11 (obj='MLW') sur simulate_higher_order(800, seed=7)."""
    from openpls.simulate import simulate_higher_order

    d = simulate_higher_order(800, seed=7)
    sem = fit_cbsem(d, Model.from_syntax(HOC_SYNTAX))
    assert sem.converged and sem.fit_indices["ddl"] == 85
    assert sem.fit_indices["chi2"] == pytest.approx(94.8992, abs=5e-3)
    cfa = fit_cbsem(d, Model.from_syntax(HOC_SYNTAX), cfa=True)
    assert cfa.fit_indices["ddl"] == 84 and cfa.fit_indices["chi2"] == pytest.approx(93.0966, abs=5e-3)
    # vrais chargements de second ordre 0,8 / 0,75 / 0,7
    np.testing.assert_allclose(sem.higher_order_loadings.to_numpy(), [0.8, 0.75, 0.7], atol=0.06)
    assert "L1" not in sem.r_squared.index and sem.path_coefficients.loc["HOC", "L1"] == 0


def test_second_order_rejects_formative_hoc():
    with pytest.raises(ValueError, match="réflectifs"):
        fit_cbsem(simulate(100), Model.from_syntax(
            "A =~ xi1_1 + xi1_2\nB =~ xi2_1 + xi2_2\nH <~ A + B\nE =~ eta1_1 + eta1_2\nE ~ H"))
