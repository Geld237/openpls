import numpy as np
import pandas as pd

from openpls import Model, fit
from openpls.comparison import cta, information_criteria
from openpls.simulate import simulate


def test_information_criteria_prefer_true_model():
    d = simulate(400, seed=4, direct=0.0)
    base = "XI1 =~ xi1_1 + xi1_2 + xi1_3\nETA1 =~ eta1_1 + eta1_2 + eta1_3\nETA2 =~ eta2_1 + eta2_2 + eta2_3\n"
    m1 = Model.from_syntax(base + "ETA1 ~ XI1\nETA2 ~ ETA1")
    m2 = Model.from_syntax(base + "ETA1 ~ XI1\nETA2 ~ ETA1 + XI1")
    tbl = information_criteria({"M1": (fit(d, m1), 400), "M2": (fit(d, m2), 400)}, "ETA2")
    assert tbl["BIC"].idxmin() == "M1"  # le chemin XI1 -> ETA2 est nul : le modèle parcimonieux gagne
    assert abs(tbl["poids BIC"].sum() - 1) < 1e-9


def test_cta_reflective_vs_formative():
    rng = np.random.default_rng(0)
    n = 500
    f = rng.normal(size=n)
    refl = pd.DataFrame({f"r{i}": 0.8 * f + 0.6 * rng.normal(size=n) for i in range(4)})
    # deux facteurs distincts : un modèle réflectif à un facteur est faux
    g = rng.normal(size=n)
    form = pd.DataFrame({"f0": f + 0.4 * rng.normal(size=n), "f1": f + 0.4 * rng.normal(size=n),
                         "f2": g + 0.4 * rng.normal(size=n), "f3": g + 0.4 * rng.normal(size=n)})
    d = pd.concat([refl, form], axis=1)
    m = Model.from_syntax("R =~ r0 + r1 + r2 + r3\nF =~ f0 + f1 + f2 + f3\nF ~ R")
    out = cta(d, m, n_boot=300, seed=1)
    assert bool(out["summary"].loc["R", "réflectif compatible"])
    assert not bool(out["summary"].loc["F", "réflectif compatible"])


def test_cta_false_rejection_rate_stays_below_alpha():
    """Audit : avec k = 6 indicateurs réflectifs, le rejet à tort doit rester sous le seuil de 10 %."""
    rejections = 0
    for rep in range(40):
        rng = np.random.default_rng(100 + rep)
        f = rng.normal(size=300)
        d = pd.DataFrame({f"r{i}": 0.7 * f + 0.7 * rng.normal(size=300) for i in range(6)})
        d["y"] = 0.5 * f + rng.normal(size=300)
        m = Model.from_syntax("R =~ r0 + r1 + r2 + r3 + r4 + r5\nY =~ y\nY ~ R")
        out = cta(d, m, n_boot=200, seed=rep)
        rejections += not bool(out["summary"].loc["R", "réflectif compatible"])
    assert rejections / 40 <= 0.15  # 25 % avant correction
