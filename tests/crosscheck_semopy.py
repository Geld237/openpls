"""Compare le CB-SEM d'OpenPLS à semopy (logiciel indépendant).

semopy exige pandas<3 : à lancer dans un environnement séparé où openpls est importable, ex.
    python -m venv /tmp/semv && /tmp/semv/bin/pip install semopy "pandas<3" scipy
    PYTHONPATH=. /tmp/semv/bin/python tests/crosscheck_semopy.py
"""
import numpy as np
import pandas as pd
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
