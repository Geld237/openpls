import numpy as np
import pytest

from openpls import Model, fit, bootstrap, quality_criteria, htmt
from openpls.simulate import simulate

MEAS = {lv: [f"{lv.lower()}_{k}" for k in (1, 2, 3)] for lv in ("XI1", "XI2", "ETA1", "ETA2")}
PATHS = [("XI1", "ETA1"), ("XI2", "ETA1"), ("ETA1", "ETA2")]


@pytest.fixture(scope="module")
def data():
    return simulate(n=2000, seed=1)


@pytest.fixture(scope="module")
def res(data):
    return fit(data, Model(MEAS, PATHS))


def test_converges(res):
    assert res.converged


def test_scores_standardized(res):
    assert np.allclose(res.scores.std(ddof=1), 1)
    assert np.allclose(res.scores.mean(), 0, atol=1e-10)


def test_attenuation_matches_theory(res):
    # PLS classique : corr(composites) = corr(facteurs) * sqrt(rho_i * rho_j).
    # Chargements 0.8 x 3 → rho = 2.4² / (2.4² + 3*0.36) ≈ 0.842 → 0.6 * 0.842 ≈ 0.505
    assert res.path_coefficients.loc["ETA1", "ETA2"] == pytest.approx(0.505, abs=0.03)


def test_plsc_recovers_true_paths(data):
    r = fit(data, Model(MEAS, PATHS), consistent=True)
    pc = r.path_coefficients
    assert pc.loc["XI1", "ETA1"] == pytest.approx(0.5, abs=0.05)
    assert pc.loc["XI2", "ETA1"] == pytest.approx(0.3, abs=0.05)
    assert pc.loc["ETA1", "ETA2"] == pytest.approx(0.6, abs=0.05)
    assert r.outer_loadings.to_numpy() == pytest.approx(0.8, abs=0.05)
    assert r.rho_a.to_numpy() == pytest.approx(0.842, abs=0.03)


def test_loadings(res):
    assert (res.outer_loadings > 0.75).all()


def test_quality(res):
    q = quality_criteria(res)
    assert (q["AVE"] > 0.5).all() and (q["rho_c"] > 0.7).all()
    h = htmt(res).to_numpy()
    h = h[~np.isnan(h)]
    assert len(h) == 6 and (h < 0.85).all()
    # HTMT estime la corrélation entre facteurs : ETA1–ETA2 vaut 0.6
    assert htmt(res).loc["ETA2", "ETA1"] == pytest.approx(0.6, abs=0.05)


@pytest.mark.parametrize("scheme", ["path", "factorial", "centroid"])
def test_schemes_agree(data, scheme):
    r = fit(data, Model(MEAS, PATHS), scheme=scheme)
    assert r.converged
    assert r.path_coefficients.loc["ETA1", "ETA2"] == pytest.approx(0.505, abs=0.03)


def test_mode_b(data):
    r = fit(data, Model(MEAS, PATHS, modes={"XI1": "B"}))
    assert r.converged


def test_bootstrap_significant(data):
    bt = bootstrap(data.iloc[:300], Model(MEAS, PATHS), n_boot=200)
    assert (bt["p_value"] < 0.01).all()


@pytest.mark.parametrize("scheme", ["path", "factorial", "centroid"])
def test_fixed_point(data, scheme):
    """Les scores finaux doivent satisfaire exactement les équations PLS (mode A) :
    Y_j ∝ X_j X_j' Z_j, avec Z = proxy interne calculé à partir de Y."""
    from openpls.algorithm import _inner_weights

    model = Model(MEAS, PATHS)
    r = fit(data, model, scheme=scheme, tol=1e-12)
    x, y = r.data_std.to_numpy(), r.scores.to_numpy()
    z = y @ _inner_weights(y, model, scheme)
    for j, lv in enumerate(model.latents):
        cols = [model.indicators.index(m) for m in MEAS[lv]]
        xj = x[:, cols]
        y_new = xj @ (xj.T @ z[:, j])
        assert abs(np.corrcoef(y_new, y[:, j])[0, 1]) == pytest.approx(1, abs=1e-9)


def test_cycle_rejected():
    with pytest.raises(ValueError):
        Model(MEAS, PATHS + [("ETA2", "XI1")])
