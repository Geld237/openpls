import numpy as np
import pandas as pd
import pytest

from openpls import Model, fit, total_effects
from openpls.ipma import ipma, rescaled_scores
from openpls.nca import ce_fdh_effect, bottleneck, nca, nca_test
from openpls.simulate import simulate

SYNTAX = """
XI1  =~ xi1_1 + xi1_2 + xi1_3
XI2  =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1 + XI1
"""


def likert(seed=0, n=400):
    d = simulate(n, seed=seed, direct=0.15)
    return d.apply(lambda c: np.clip(np.round(4 + 1.2 * c), 1, 7))


def test_ipma_scores_and_weights():
    d = likert()
    m = Model.from_syntax(SYNTAX)
    res = fit(d, m)
    sc, w = rescaled_scores(res, d, scale=(1, 7))
    assert ((sc >= 0) & (sc <= 100)).all().all()
    np.testing.assert_allclose(w.groupby(level=0).sum().to_numpy(), 1.0)


def test_ipma_importance_consistent_with_standardized_effects():
    """Avec une seule latente par équation, effet non standardisé = effet standardisé × sd(Y)/sd(X)."""
    d = likert(1)
    m = Model.from_syntax("XI1 =~ xi1_1 + xi1_2 + xi1_3\nETA1 =~ eta1_1 + eta1_2 + eta1_3\nETA1 ~ XI1")
    res = fit(d, m)
    out = ipma(res, d, "ETA1", scale=(1, 7))
    sc = out["scores"]
    # corrélation des scores 0-100 (poids déstandardisés) * ratio des écarts-types
    expected = np.corrcoef(sc["XI1"], sc["ETA1"])[0, 1] * sc["ETA1"].std() / sc["XI1"].std()
    assert out["latents"].loc["XI1", "importance"] == pytest.approx(expected, rel=1e-10)
    assert 0 < out["target_performance"] < 100


def test_ipma_full_model():
    d = likert(2)
    res = fit(d, Model.from_syntax(SYNTAX))
    out = ipma(res, d, "ETA2", scale=(1, 7))
    lat = out["latents"]
    assert set(lat.index) == {"XI1", "XI2", "ETA1"}
    assert (lat["importance"] > 0).all()
    ind = out["indicators"]
    np.testing.assert_allclose(ind.groupby(level=0)["importance"].sum().reindex(lat.index), lat["importance"])
    np.testing.assert_allclose(ind.loc[("XI1", "xi1_1"), "performance"],
                               100 * (d["xi1_1"].mean() - 1) / 6)


def test_ce_fdh_known_values():
    # points dans le triangle y <= x : d -> 0,5
    rng = np.random.default_rng(0)
    x = rng.uniform(size=20000)
    y = x * rng.uniform(size=20000)
    assert ce_fdh_effect(x, y) == pytest.approx(0.5, abs=0.02)
    # petit exemple calculé à la main : plafond 0 sur [0,1), 2 sur [1,2) ; zone vide = 2·1 + 0·1 = 2, scope = 2·2
    assert ce_fdh_effect([0, 1, 2], [0, 2, 1]) == pytest.approx(0.5)
    bn = bottleneck(np.array([0, 1, 2.0]), np.array([0, 2, 1.0]), steps=[0, 50, 100])
    assert np.isnan(bn["0 %"]) and bn["50 %"] == pytest.approx(50) and bn["100 %"] == pytest.approx(50)


def test_nca_permutation():
    rng = np.random.default_rng(1)
    x = rng.uniform(size=300)
    assert nca_test(x, x * rng.uniform(size=300), n_perm=200)["p_value"] < 0.01
    assert nca_test(x, rng.uniform(size=300), n_perm=200)["p_value"] > 0.05


def test_nca_on_model():
    d = simulate(300, seed=3)
    res = fit(d, Model.from_syntax(SYNTAX))
    out = nca(res, "ETA1", n_perm=100)
    assert list(out["effects"].index) == ["XI1", "XI2"]
    assert out["bottleneck"].shape == (11, 2)
