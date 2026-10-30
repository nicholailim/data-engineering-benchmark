"""
03_mcda_weight_sensitivity.py
Reproduces the weight-sensitivity analysis of the multi-criteria decision model
(Section 4.5, Table 6): alternative weight sets, one-at-a-time weight changes,
weight thresholds at which the leader changes, random (Dirichlet) weights, and
one-at-a-time changes of the criterion scores.

Criterion scores (1-5) are the ones in Table 5 of the paper; they are author
judgements, not measurements.  Run from the repository root:
    python scripts/03_mcda_weight_sensitivity.py
"""
import os
import numpy as np
import pandas as pd

CRITERIA = ['Cost', 'Scalability', 'Complexity', 'Lock-in', 'Sustainability']
BASE_W = np.array([.30, .20, .25, .15, .10])
SCORES = {                       # Table 5
    'AWS Glue':      np.array([4, 5, 3, 2, 4]),
    'Azure ADF':     np.array([3, 4, 4, 2, 4]),
    'GCP Dataflow':  np.array([5, 4, 3, 3, 5]),
}
NAMES = list(SCORES)

def totals(w):
    return {k: float(v @ w) for k, v in SCORES.items()}

# ---- sanity check against Table 5 -------------------------------------------
t0 = totals(BASE_W)
assert abs(t0['AWS Glue'] - 3.65) < 1e-9 and abs(t0['Azure ADF'] - 3.40) < 1e-9 and abs(t0['GCP Dataflow'] - 4.00) < 1e-9

# ---- Table 6: alternative weight sets ---------------------------------------
SETS = {
    'Baseline':           BASE_W,
    'Equal weights':      np.ones(5) / 5,
    'Cost-led':           np.array([.50, .15, .15, .10, .10]),
    'Delivery-led':       np.array([.15, .20, .40, .15, .10]),
    'Risk-averse':        np.array([.20, .15, .25, .30, .10]),
    'Sustainability-led': np.array([.20, .15, .20, .10, .35]),
    'No sustainability':  np.array([.33, .22, .28, .17, .00]),
}
rows = []
for name, w in SETS.items():
    t = totals(w)
    rows.append({'Weight set': name,
                 'Weights (%)': '/'.join(str(round(x * 100)) for x in w),
                 **{k: round(v, 3) for k, v in t.items()},
                 'Top': max(t, key=t.get)})
table6 = pd.DataFrame(rows)
print('\nTable 6 - weighted scores under alternative weight sets\n', table6.to_string(index=False))

# ---- one-at-a-time +/-10 percentage points (others rescaled proportionally) --
def oat(i, delta):
    w = BASE_W.copy()
    new = max(0.0, w[i] + delta)
    others = [j for j in range(5) if j != i]
    w[others] = BASE_W[others] / BASE_W[others].sum() * (1 - new)
    w[i] = new
    return w
oat_leaders = []
for i in range(5):
    for d in (-.10, .10):
        t = totals(oat(i, d)); oat_leaders.append(max(t, key=t.get))
print('\n+/-10-point changes: GCP Dataflow first in',
      sum(l == 'GCP Dataflow' for l in oat_leaders), 'of', len(oat_leaders))

# ---- weight thresholds where the leader changes -------------------------------
print('\nLeader as one weight is raised (others rescaled proportionally):')
for i, c in enumerate(CRITERIA):
    prev, flips = None, []
    for x in np.linspace(0, 1, 1001):
        w = BASE_W.copy()
        others = [j for j in range(5) if j != i]
        w[others] = BASE_W[others] / BASE_W[others].sum() * (1 - x)
        w[i] = x
        t = totals(w); lead = max(t, key=t.get)
        if lead != prev:
            flips.append((round(float(x), 3), lead)); prev = lead
    print(f'  {c:15s}', flips)

# ---- random weights (Dirichlet), seed 42, draw order as used for the paper ----
rng = np.random.default_rng(42)
def lead_share(W):
    T = np.stack([W @ SCORES[k] for k in NAMES], 1)
    return {k: round(float((np.argmax(T, 1) == i).mean() * 100), 1) for i, k in enumerate(NAMES)}
res = {}
for label, alpha in [('flat Dirichlet(1)', np.ones(5)),
                     ('Dirichlet centred on baseline, concentration 20', BASE_W * 20),
                     ('Dirichlet centred on baseline, concentration 10', BASE_W * 10)]:
    res[label] = lead_share(rng.dirichlet(alpha, 100000))
    print(f'\n{label}: share of 100,000 draws in which each platform ranks first\n  ', res[label])

# ---- one-at-a-time changes of +/-1 in each of the 15 scores -------------------
kept, total = 0, 0
for k in NAMES:
    for i in range(5):
        for d in (-1, 1):
            s = {a: v.copy() for a, v in SCORES.items()}
            new = min(5, max(1, s[k][i] + d))
            if new == s[k][i]:
                continue                       # score already at the 1-5 limit
            s[k][i] = new
            t = {a: float(v @ BASE_W) for a, v in s.items()}
            total += 1
            kept += max(t, key=t.get) == 'GCP Dataflow'
print(f'\n+/-1 score changes: GCP Dataflow first in {kept} of {total} feasible changes')

os.makedirs('outputs', exist_ok=True)
table6.to_csv('outputs/table6_weight_sets.csv', index=False)
print('\nSaved outputs/table6_weight_sets.csv')
