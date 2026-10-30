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
