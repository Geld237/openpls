import numpy as np
import pytest

from openpls import Model, fit
from openpls.effects import (
    classify_mediation,
    mediation_analysis,
    mediation_paths,
    specific_indirect_effects,
    total_effects,
)
from openpls.simulate import simulate

MEAS = {lv: [f"{lv.lower()}_{k}" for k in (1, 2, 3)] for lv in ("XI1", "XI2", "ETA1", "ETA2")}
# On estime TOUJOURS le chemin direct XI1 -> ETA2 pour pouvoir tester la médiation
PATHS = [("XI1", "ETA1"), ("XI2", "ETA1"), ("ETA1", "ETA2"), ("XI1", "ETA2")]


def test_paths_enumeration():
    m = Model(MEAS, PATHS)
    names = {" -> ".join(m.latents[i] for i in p) for p in mediation_paths(m)}
    assert names == {"XI1 -> ETA1 -> ETA2", "XI2 -> ETA1 -> ETA2"}


def test_total_equals_direct_plus_indirect():
    r = fit(simulate(800, seed=3), Model(MEAS, PATHS), consistent=True)
    b = r.path_coefficients
    ind = specific_indirect_effects(r)
    t = total_effects(r)
    assert t.loc["XI1", "ETA2"] == pytest.approx(b.loc["XI1", "ETA2"] + ind["XI1 -> ETA1 -> ETA2"])
    assert t.loc["XI2", "ETA2"] == pytest.approx(ind["XI2 -> ETA1 -> ETA2"])
    assert t.loc["XI2", "ETA2"] == pytest.approx(b.loc["XI2", "ETA1"] * b.loc["ETA1", "ETA2"])


def test_plsc_recovers_true_indirect():
    r = fit(simulate(3000, seed=4), Model(MEAS, PATHS), consistent=True)
    ind = specific_indirect_effects(r)
    assert ind["XI1 -> ETA1 -> ETA2"] == pytest.approx(0.5 * 0.6, abs=0.04)
    assert ind["XI2 -> ETA1 -> ETA2"] == pytest.approx(0.3 * 0.6, abs=0.04)


def test_full_mediation_detected():
    data = simulate(600, seed=5, direct=0.0)
    med, boot = mediation_analysis(data, Model(MEAS, PATHS), n_boot=300, consistent=True)
    row = med.loc["XI1 -> ETA1 -> ETA2"]
    assert row["indirect_significatif"]
    assert row["type_mediation"] == "indirecte seule (totale)"
    assert ("total", "XI1 -> ETA2") in boot.index


def test_partial_mediation_detected():
    data = simulate(600, seed=6, direct=0.3)
    med, _ = mediation_analysis(data, Model(MEAS, PATHS), n_boot=300, consistent=True)
    assert med.loc["XI1 -> ETA1 -> ETA2", "type_mediation"] == "complémentaire (partielle)"


def test_no_direct_path_is_not_called_full_mediation():
    data = simulate(600, seed=5)
    paths = [p for p in PATHS if p != ("XI1", "ETA2")]
    med, _ = mediation_analysis(data, Model(MEAS, paths), n_boot=200)
    assert all("indéterminé" in t for t in med["type_mediation"])


def test_classification_table():
    assert classify_mediation(True, True, 0.2, -0.1) == "compétitive (partielle)"
    assert classify_mediation(True, False, 0.2, 0.0) == "directe seule (pas de médiation)"
    assert classify_mediation(False, False, 0.0, 0.0) == "aucun effet"


def test_serial_mediation():
    # Chaîne à 3 arcs : A -> B -> C -> D
    rng = np.random.default_rng(0)
    n = 1500
    a = rng.normal(size=n)
    b = 0.6 * a + rng.normal(0, 0.8, n)
    c = 0.6 * b + rng.normal(0, 0.8, n)
    d = 0.6 * c + rng.normal(0, 0.8, n)
    import pandas as pd

    df = pd.DataFrame({f"{nm}{k}": v + rng.normal(0, 0.3, n) for nm, v in zip("abcd", (a, b, c, d)) for k in (1, 2)})
    m = Model({L.upper(): [f"{L}1", f"{L}2"] for L in "abcd"}, [("A", "B"), ("B", "C"), ("C", "D")])
    r = fit(df, m)
    ind = specific_indirect_effects(r)
    assert set(ind.index) == {"A -> B -> C", "B -> C -> D", "A -> B -> C -> D"}
    pc = r.path_coefficients
    assert ind["A -> B -> C -> D"] == pytest.approx(pc.loc["A", "B"] * pc.loc["B", "C"] * pc.loc["C", "D"])
    assert total_effects(r).loc["A", "D"] == pytest.approx(ind["A -> B -> C -> D"])
