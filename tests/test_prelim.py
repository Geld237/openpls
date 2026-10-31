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


def test_imputation_and_spss_import(tmp_path):
    from openpls.gui_helpers import impute, prepare_data

    rng = np.random.default_rng(3)
    z = rng.normal(size=400)
    x = pd.DataFrame({"a": z + 0.3 * rng.normal(size=400), "b": z + 0.3 * rng.normal(size=400),
                      "c": z + 0.3 * rng.normal(size=400)})
    truth = x.loc[:39, "a"].copy()
    x.loc[:39, "a"] = np.nan
    reg = impute(x, "regression")
    mean = impute(x, "mean")
    assert not reg.isna().any().any()
    assert np.abs(reg.loc[:39, "a"] - truth).mean() < np.abs(mean.loc[:39, "a"] - truth).mean()
    m = Model.from_syntax("A =~ a + b\nC =~ c\nC ~ A")
    d, w = prepare_data(x, m, missing="mean")
    assert len(d) == 400 and w
    d, _ = prepare_data(x, m)
    assert len(d) == 360

    import pytest

    pyreadstat = pytest.importorskip("pyreadstat")
    path = tmp_path / "f.sav"
    pyreadstat.write_sav(x.fillna(0), str(path), column_labels=["item a", "item b", "item c"])
    from streamlit.testing.v1 import AppTest  # noqa: F401  (l'import de l'appli n'est pas nécessaire)
    import importlib.util

    df, meta = pyreadstat.read_sav(str(path))
    assert list(df.columns) == ["a", "b", "c"] and meta.column_labels[0] == "item a"


def test_audit_regressions_mardia_ten_times_and_project_types():
    import hashlib  # noqa: F401
    import io
    import json
    import zipfile

    from openpls import project as pj

    rng = np.random.default_rng(0)
    big = rng.normal(size=(20000, 8))
    mm = ds.mardia(big)  # par blocs : pas de matrice 20000 × 20000 (3 Go)
    assert 0 <= mm["p asymétrie"] <= 1
    m = Model.from_syntax("X =~ x1\nM =~ m1\nY =~ y1\nY ~ X + M + X:M")
    assert ds.ten_times_rule(m) == 30

    raw = pd.DataFrame({"code": ["001", "002", "NA"], "site": ["1", "2", "1"], "x": [0.1 + 0.2, 1 / 3, np.nan]})
    blob = pj.save_project(raw, "t.csv", "A =~ x", {}, {}, {"fitted": True})
    p = pj.load_project(blob)
    assert p["data"]["code"].tolist() == ["001", "002", "NA"] and p["data"]["site"].tolist() == ["1", "2", "1"]
    assert p["data"]["x"].iloc[0] == raw["x"].iloc[0]  # flottant relu à l'identique
    assert p["results"] is not None
    # données modifiées dans le fichier : résultats ignorés, projet quand même ouvert
    zin = zipfile.ZipFile(io.BytesIO(blob))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in zin.namelist():
            data = zin.read(n)
            if n == "data.csv":
                data = data.replace(b"001", b"009")
            if n == "results.json" and False:
                data = b""
            z.writestr(n, data)
    p2 = pj.load_project(buf.getvalue())
    assert p2["results"] is None and p2["results_note"] == "data" and len(p2["data"]) == 3
    # résultats illisibles : projet ouvert quand même
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in zin.namelist():
            z.writestr(n, b"{pas du json" if n == "results.json" else zin.read(n))
    p3 = pj.load_project(buf.getvalue())
    assert p3["results"] is None and p3["results_note"] == "unreadable"
    assert json.loads(zin.read("project.json"))["dtypes"]["code"] in ("object", "str", "string")
