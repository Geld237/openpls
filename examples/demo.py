"""Démo : python examples/demo.py  (ou passe ton propre CSV : python examples/demo.py data.csv)"""
import sys

import pandas as pd

from openpls import Model, fit, bootstrap
from openpls.simulate import simulate

if len(sys.argv) > 1:
    data = pd.read_csv(sys.argv[1])
else:
    data = simulate(n=500)

model = Model(
    measurement={
        "XI1": ["xi1_1", "xi1_2", "xi1_3"],
        "XI2": ["xi2_1", "xi2_2", "xi2_3"],
        "ETA1": ["eta1_1", "eta1_2", "eta1_3"],
        "ETA2": ["eta2_1", "eta2_2", "eta2_3"],
    },
    structural=[("XI1", "ETA1"), ("XI2", "ETA1"), ("ETA1", "ETA2")],
)

res = fit(data, model)
print(res.summary())
print("\n== Bootstrap (1000 tirages) ==")
print(bootstrap(data, model, n_boot=1000).round(4).to_string())
