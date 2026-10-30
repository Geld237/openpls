"""Non-régression des corrections issues de l'audit v0.4."""
import numpy as np
import pytest

from openpls import Model, fit
from openpls.cbsem import fit_cbsem
from openpls.simulate import simulate

M = Model.from_syntax("A =~ xi1_1 + xi1_2 + xi1_3\nB =~ eta1_1 + eta1_2 + eta1_3\nB ~ A")


def test_cbsem_refuses_unidentified_model():
    with pytest.raises(ValueError, match="non identifié"):
        fit_cbsem(simulate(200), Model.from_syntax("A =~ xi1_1\nB =~ eta1_1\nB ~ A"))


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

