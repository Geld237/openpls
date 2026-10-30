"""OpenPLS contre une implémentation de référence indépendante (tests/reference_pls.py).

Remplace plspm comme référence principale : plspm s'arrête avant convergence (écart ~8e-3),
alors que les deux implémentations convergentes concordent à la précision machine."""
import numpy as np
import pytest

from openpls import Model, fit
from openpls.simulate import simulate
from reference_pls import mypls

LVS = ["XI1", "XI2", "ETA1", "ETA2"]
PATHS = [("XI1", "ETA1"), ("XI2", "ETA1"), ("ETA1", "ETA2"), ("XI1", "ETA2")]
MEAS = {lv: [f"{lv.lower()}_{k}" for k in (1, 2, 3)] for lv in LVS}


@pytest.fixture(scope="module")
def data():
    d = simulate(n=200, seed=7, direct=0.2)
    d["xi2_3"] = d["xi2_3"] * 0.3 + np.random.default_rng(3).normal(size=200)  # bloc hétérogène
    return d


@pytest.mark.parametrize("scheme", ["path", "factorial", "centroid"])
@pytest.mark.parametrize("modes", [{}, {"XI2": "B"}, {"XI2": "B", "ETA2": "B"}], ids=["A", "1B", "2B"])
def test_matches_independent_reference(data, scheme, modes):
    ref = mypls(data, MEAS, PATHS, modes, scheme)
    res = fit(data, Model(MEAS, PATHS, modes=dict(modes)), scheme=scheme, tol=1e-12, max_iter=5000)
    assert res.converged
    for s, d in PATHS:
        assert res.path_coefficients.loc[s, d] == pytest.approx(ref["B"].loc[s, d], abs=1e-10)
    for lv in LVS:
        np.testing.assert_allclose(res.outer_loadings[lv].to_numpy(), ref["load"][lv], atol=1e-10)
        np.testing.assert_allclose(res.outer_weights[lv].to_numpy(), ref["W"][lv], atol=1e-10)
