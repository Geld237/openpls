import numpy as np
import pandas as pd
import pytest

from openpls import Model, fit
from openpls.fimix import fimix
from openpls.simulate import simulate

SYNTAX = """
XI1  =~ xi1_1 + xi1_2 + xi1_3
XI2  =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1
"""


def test_single_segment_equals_ols():
    d = simulate(300, seed=0)
    res = fit(d, Model.from_syntax(SYNTAX))
    out = fimix(res, segments=[1])
    sc = res.scores
    beta = np.linalg.lstsq(sc[["XI1", "XI2"]], sc["ETA1"], rcond=None)[0]
    np.testing.assert_allclose(out["solutions"][1]["paths"].loc[["XI1 -> ETA1", "XI2 -> ETA1"], "segment 1"],
                               beta, atol=1e-8)


def test_recovers_two_segments():
    a = simulate(400, seed=1, eta_path=0.8)
    b = simulate(300, seed=2, eta_path=-0.5)
    d = pd.concat([a, b], ignore_index=True)
    truth = np.repeat([1, 2], [400, 300])
    res = fit(d, Model.from_syntax(SYNTAX))
    out = fimix(res, segments=[1, 2, 3], starts=5)
    crit = out["criteria"]
    assert crit["BIC"].idxmin() == 2 and crit["CAIC"].idxmin() == 2
    sol = out["solutions"][2]
    assert sol["sizes"].iloc[0] == pytest.approx(4 / 7, abs=0.07)
    p = sol["paths"].loc["ETA1 -> ETA2"]
    assert p.max() > 0.5 and p.min() < -0.3
    agree = (sol["membership"].to_numpy() == truth).mean()
    # plafond théorique : classement bayésien avec les vrais paramètres de chaque segment
    from scipy.stats import norm
    sc, ll = res.scores, []
    for g in (1, 2):
        m = truth == g
        x, y = sc.loc[m, "ETA1"], sc.loc[m, "ETA2"]
        b = (x @ y) / (x @ x)
        ll.append(np.log(m.mean()) + norm.logpdf(sc["ETA2"], b * sc["ETA1"], np.std(y - b * x)))
    oracle = (np.argmax(ll, axis=0) + 1 == truth).mean()
    assert max(agree, 1 - agree) >= oracle - 0.05, (agree, oracle)
    assert 0 < crit.loc[2, "EN"] < 1  # segments très recouvrants ici : EN faible, comme attendu
