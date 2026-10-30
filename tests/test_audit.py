"""Non-régression des corrections issues de l'audit v0.4."""
import numpy as np
import pytest

from openpls import Model, fit
from openpls.cbsem import fit_cbsem
from openpls.simulate import simulate

M = Model.from_syntax("A =~ xi1_1 + xi1_2 + xi1_3\nB =~ eta1_1 + eta1_2 + eta1_3\nB ~ A")


def test_cbsem_refuses_unidentified_model():
    # construit isolé à 2 indicateurs : 4 paramètres pour 3 moments
    with pytest.raises(ValueError, match="non identifié"):
        fit_cbsem(simulate(200), Model.from_syntax("A =~ xi1_1 + xi1_2"))


def test_cbsem_refuses_singular_covariance():
    with pytest.raises(ValueError, match="singulière"):
        fit_cbsem(simulate(200).head(4), M)


def test_non_numeric_values_are_named():
    d = simulate(100).astype(object)
    assert np.isfinite(fit(d, M).path_coefficients.loc["A", "B"])   # objets numériques acceptés
    d.loc[3, "xi1_2"] = "n/a"
    with pytest.raises(ValueError, match="xi1_2"):
        fit(d, M)


def test_gui_binds_to_localhost(monkeypatch):
    import sys
    from openpls import gui

    seen = {}

    class FakeCli:
        @staticmethod
        def main():
            seen["argv"] = list(sys.argv)
            return 0

    monkeypatch.setitem(sys.modules, "streamlit.web.cli", FakeCli)
    monkeypatch.setattr(sys, "argv", ["openpls-gui"])
    import streamlit.web as sw
    monkeypatch.setattr(sw, "cli", FakeCli, raising=False)
    with pytest.raises(SystemExit):
        gui.main()
    assert "--server.address=localhost" in seen["argv"]



# ---------------------------------------------------------------- audit indépendant
import pandas as pd

from openpls import bootstrap, f_squared, fornell_larcker, quality_criteria
from openpls.bootstrap import BootstrapWarning
from openpls.mga import mga

FULL = Model.from_syntax("""XI1 =~ xi1_1 + xi1_2 + xi1_3
XI2 =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1 + XI1""")


def test_bootstrap_failures_are_reported():
    rng = np.random.default_rng(2)
    n = 80
    a = rng.normal(size=n)
    b = 0.4 * a + rng.normal(0, 0.9, n)
    d = pd.DataFrame({"a1": 0.3 * a + rng.normal(size=n), "a2": 0.3 * a + rng.normal(size=n),
                      **{f"b{k}": 0.8 * b + rng.normal(0, .6, n) for k in (1, 2, 3)}})
    m = Model.from_syntax("A =~ a1 + a2\nB =~ b1 + b2 + b3\nB ~ A")
    with pytest.warns(BootstrapWarning, match="NON fiable"):
        bt = bootstrap(d, m, n_boot=200, consistent=True)
    assert bt.attrs["failure_rate"] > 0.05 and bt.attrs["n_boot_inadmissible"] > 0


def test_f2_inherits_plsc_and_scheme():
    d = simulate(400, seed=3, direct=0.15)
    res = fit(d, FULL, consistent=True, scheme="factorial")
    explicit = f_squared(res, d, consistent=True, scheme="factorial")
    pd.testing.assert_frame_equal(f_squared(res, d), explicit)


def test_duplicate_indicator_rejected():
    with pytest.raises(ValueError, match="xi1_2"):
        Model.from_syntax("A =~ xi1_1 + xi1_2\nB =~ xi1_2 + eta1_1\nB ~ A")
    with pytest.raises(ValueError, match="deux fois"):
        Model.from_syntax("A =~ xi1_1 + xi1_1\nB =~ eta1_1\nB ~ A")


def test_mga_aligns_series_by_label():
    d = pd.concat([simulate(200, seed=1), simulate(200, seed=2, eta_path=0.0)], ignore_index=True)
    g = pd.Series(np.repeat(["A", "B"], 200), index=d.index)
    shuffled = g.sample(frac=1, random_state=0)       # même contenu, ordre d'index différent
    m = Model.from_syntax(FULL.to_syntax().replace("ETA2 ~  ETA1 + XI1", "ETA2 ~ ETA1"))
    a = mga(d, m, g, n_perm=20, n_boot=10, seed=0)["comparison"]
    b = mga(d, m, shuffled, n_perm=20, n_boot=10, seed=0)["comparison"]
    pd.testing.assert_series_equal(a["difference"], b["difference"])
    with pytest.raises(ValueError, match="ne couvre pas"):
        mga(d, m, g.iloc[:300], n_perm=10, n_boot=10)


def test_fornell_larcker_uses_corrected_correlations_under_plsc():
    d = simulate(3000, seed=4, loading=0.7)
    res = fit(d, FULL, consistent=True)
    fl = fornell_larcker(res)
    assert fl.loc["ETA1", "XI1"] == pytest.approx(res.latent_correlations.loc["ETA1", "XI1"])
    assert fl.loc["ETA1", "XI1"] > res.scores[["ETA1", "XI1"]].corr().iloc[0, 1] + 0.05


def test_formative_blocks_have_no_reliability():
    res = fit(simulate(200), Model.from_syntax("A <~ xi1_1 + xi1_2 + xi1_3\nB =~ eta1_1 + eta1_2\nB ~ A"))
    q = quality_criteria(res)
    assert q.loc["A"].isna().all() and q.loc["B"].notna().all()


def test_cbsem_single_indicator_equals_path_analysis():
    rng = np.random.default_rng(0)
    x1, x2 = rng.normal(size=(2, 500))
    y = 0.4 * x1 + 0.3 * x2 + rng.normal(size=500)
    d = pd.DataFrame({"a": x1, "b": x2, "c": y})
    r = fit_cbsem(d, Model.from_syntax("A =~ a\nB =~ b\nC =~ c\nC ~ A + B"))
    z = lambda v: (v - v.mean()) / v.std()  # noqa: E731
    beta = np.linalg.lstsq(np.column_stack([z(x1), z(x2)]), z(y), rcond=None)[0]
    np.testing.assert_allclose(r.path_coefficients.loc[["A", "B"], "C"], beta, atol=1e-6)
    assert r.fit_indices["ddl"] == 0
