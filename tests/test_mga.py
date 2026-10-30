import numpy as np
import pandas as pd
import pytest

from openpls import Model
from openpls.mga import mga
from openpls.simulate import simulate

SYNTAX = """
XI1  =~ xi1_1 + xi1_2 + xi1_3
XI2  =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1
"""
M = Model.from_syntax(SYNTAX)


def two_groups(path2=0.6, shift=0.0, n=300):
    a = simulate(n, seed=101)
    b = simulate(n, seed=201, eta_path=path2)
    b[["eta2_1", "eta2_2", "eta2_3"]] += shift
    return pd.concat([a, b], ignore_index=True), np.repeat(["A", "B"], n)


def test_detects_path_difference():
    d, g = two_groups(path2=0.15)
    out = mga(d, M, g, n_perm=200, n_boot=200, seed=0)
    c = out["comparison"]
    assert c.loc["ETA1 -> ETA2", "difference"] > 0.3
    for col in ("p_permutation", "p_henseler", "p_welch"):
        assert c.loc["ETA1 -> ETA2", col] < 0.01, col
    assert c.loc["XI1 -> ETA1", "p_permutation"] > 0.05
    # les exogènes restent invariants ; ETA2 (lien interne faible dans B) peut ne pas l'être
    assert out["micom_step2"].loc[["XI1", "XI2"], "invariance compositionnelle"].all()


def test_no_difference_and_full_invariance():
    d, g = two_groups()
    out = mga(d, M, g, n_perm=200, n_boot=200, seed=0)
    assert not out["comparison"]["différence significative (perm., 5 %)"].any()
    assert out["micom_step2"]["c"].min() > 0.99
    assert out["micom_step2"]["invariance compositionnelle"].all()
    assert out["verdict"].startswith("invariance totale")


def test_micom_detects_mean_difference():
    d, g = two_groups(shift=0.8)
    out = mga(d, M, g, n_perm=200, n_boot=50, seed=0)
    s3 = out["micom_step3"]
    assert not s3.loc["ETA2", "égalité moyennes"] and s3.loc["ETA2", "p_moyenne"] < 0.01
    assert s3.loc["XI1", "égalité moyennes"]
    assert out["verdict"].startswith("invariance partielle")


def test_group_validation():
    d = simulate(100)
    with pytest.raises(ValueError, match="2 groupes"):
        mga(d, M, np.repeat(["a", "b", "c", "d"], 25), n_perm=10, n_boot=10)
