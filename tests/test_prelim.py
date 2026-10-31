import numpy as np
import pandas as pd

from openpls import Model
from openpls import descriptives as ds
from openpls.simulate import simulate


def test_descriptives_and_missing():
    d = simulate(200, seed=1)
    d.loc[0, "xi1_1"] = np.nan
    m = Model.from_syntax("XI1 =~ xi1_1 + xi1_2 + xi1_3\nETA1 =~ eta1_1 + eta1_2 + eta1_3\nETA1 ~ XI1")
    blocks = ds.indicator_blocks(m, list(d.columns))
    desc = ds.descriptive_statistics(d, blocks)
    assert desc.loc[("XI1", "xi1_1"), "manquants"] == 1
    assert abs(desc.loc[("XI1", "xi1_2"), "moyenne"] - d["xi1_2"].mean()) < 1e-12
    ms = ds.missing_summary(d, list(blocks))
    assert ms["complete_rows"] == 199


def test_mardia_detects_non_normality():
    rng = np.random.default_rng(0)
    normal = ds.mardia(rng.normal(size=(500, 4)))
    skewed = ds.mardia(rng.exponential(size=(500, 4)))
    assert normal["p asymétrie"] > 0.01 and skewed["p asymétrie"] < 0.001


def test_outliers_harman_vif_and_sample_size():
    rng = np.random.default_rng(1)
    x = pd.DataFrame(rng.normal(size=(300, 5)), columns=list("abcde"))
    x.iloc[7] = 12
    out = ds.mahalanobis_outliers(x, list(x.columns))
    assert out.index[0] == 7 and out.loc[7, "aberrante"]
    hm = ds.harman_single_factor(x, list(x.columns))
    assert hm["pct_first"] < 50
    vif = ds.full_collinearity_vif(x)
    assert (vif > 0.9).all() and (vif < 1.5).all()
    assert ds.inverse_square_root_n(0.2) == 155  # Kock & Hadaya (2018), tableau 1
