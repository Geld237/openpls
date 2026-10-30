"""Compare le CB-SEM d'OpenPLS à semopy (logiciel indépendant).

semopy exige pandas<3 : à lancer dans un environnement séparé où openpls est importable, ex.
    python -m venv /tmp/semv && /tmp/semv/bin/pip install semopy "pandas<3" scipy
    PYTHONPATH=. /tmp/semv/bin/python tests/crosscheck_semopy.py
"""
import semopy

from openpls import Model
from openpls.cbsem import fit_cbsem
from openpls.simulate import simulate

DESC = """XI1 =~ xi1_1 + xi1_2 + xi1_3
XI2 =~ xi2_1 + xi2_2 + xi2_3
ETA1 =~ eta1_1 + eta1_2 + eta1_3
ETA2 =~ eta2_1 + eta2_2 + eta2_3
ETA1 ~ XI1 + XI2
ETA2 ~ ETA1 + XI1"""

d = simulate(500, seed=0, direct=0.15)
ours = fit_cbsem(d, Model.from_syntax(DESC))
ref = semopy.Model(DESC)
ref.fit(d, obj="MLW")
ins = ref.inspect()
chi2_ref = semopy.calc_stats(ref).T.loc["chi2", "Value"]
print(f"chi2 : OpenPLS {ours.fit_indices['chi2']:.4f}  semopy {chi2_ref:.4f}")
worst = 0.0
for _, r in ins.iterrows():
    key = f"{r.rval} =~ {r.lval}" if r.op == "=~" else f"{r.lval} ~ {r.rval}" if r.op == "~" else None
    if key in ours.estimates.index:
        diff = abs(r.Estimate - ours.estimates.loc[key, "estimate"])
        worst = max(worst, diff)
        print(f"{key:<16} semopy {r.Estimate: .4f}  OpenPLS {ours.estimates.loc[key, 'estimate']: .4f}")
print(f"écart maximal : {worst:.2e}")
assert worst < 2e-3 and abs(chi2_ref - ours.fit_indices["chi2"]) < 1e-2


# ---------------------------------------------------------------- second ordre (SEM et CFA)
from openpls.simulate import simulate_higher_order

HOC = """X =~ x_1 + x_2 + x_3
L1 =~ l1_1 + l1_2 + l1_3
L2 =~ l2_1 + l2_2 + l2_3
L3 =~ l3_1 + l3_2 + l3_3
Y =~ y_1 + y_2 + y_3
HOC =~ L1 + L2 + L3
"""
d2 = simulate_higher_order(800, seed=7)
for cfa, extra in ((False, "HOC ~ X\nY ~ HOC"), (True, "HOC ~~ X\nHOC ~~ Y\nX ~~ Y")):
    ours = fit_cbsem(d2, Model.from_syntax(HOC + "HOC ~ X\nY ~ HOC"), cfa=cfa)
    ref = semopy.Model(HOC + extra)
    ref.fit(d2, obj="MLW")
    chi2_ref = semopy.calc_stats(ref).T.loc["chi2", "Value"]
    worst = 0.0
    children = set(d2.columns) | {"L1", "L2", "L3"}
    for _, r in ref.inspect().iterrows():
        if r.op != "~":
            continue
        key = f"{r.rval} =~ {r.lval}" if r.lval in children else f"{r.lval} ~ {r.rval}"
        if key in ours.estimates.index:
            worst = max(worst, abs(r.Estimate - ours.estimates.loc[key, "estimate"]))
    label = "CFA 2nd ordre" if cfa else "SEM 2nd ordre"
    print(f"{label} : chi2 OpenPLS {ours.fit_indices['chi2']:.4f}  semopy {chi2_ref:.4f}  écart max {worst:.1e}")
    assert worst < 2e-3 and abs(chi2_ref - ours.fit_indices["chi2"]) < 1e-2
