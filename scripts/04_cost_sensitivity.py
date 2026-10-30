"""
04_cost_sensitivity.py
Re-runs the cost and total-cost-of-ownership (TCO) model of Section 3.2 under
alternative assumptions (Section 4.6, Table 7).

The model below re-implements the formulas of 02_cloud_cost_model.py in a
parameterised form.  Before any sensitivity run it checks that the baseline
reproduces the published results (monthly costs, break-even months, 36-month
net savings), so the two scripts cannot silently diverge.

Run from the repository root:
    python scripts/04_cost_sensitivity.py
"""
import os
import pandas as pd

# ------------------------------- inputs (Table 2) ------------------------------
PHP_PER_USD = 59.0                      # April 2025, as coded in the model
STORAGE_GB = 100
SECONDARY = {'AWS Glue': 4 + 9 + 4,     # monitoring, egress, secrets (USD/month)
             'Azure ADF': 3 + 8.7 + 3,
             'GCP Dataflow': 0 + 8 + 0.6}
MIGRATION = {'AWS Glue': 4200, 'Azure ADF': 4000, 'GCP Dataflow': 4100}   # one-time USD
STAGING_SHARE, STAGING_MONTHS = 0.20, 6
GROWTH, HORIZON = 1.20, 36
BASE_GB, BASE_JOBS = 500, 300

def glue(gb, jobs, dur=0.5, rate=0.44):
    return 2 * dur * jobs * rate + (jobs / 10) * 2 * (6 / 60) * 0.44 + STORAGE_GB * 0.025

def adf(gb, jobs, dur=0.5, vcores=8):
    return ((jobs / 1000) * 1.0 + jobs * 2 * (15 / 60) * 4 * 0.25
            + jobs * dur * vcores * 0.268 + STORAGE_GB * 0.02)

def dataflow(gb, jobs, dur=0.5):
    return (4 * dur * jobs * 0.07 + 15 * dur * jobs * 0.0044463
            + gb * 0.10 * 0.01357 + STORAGE_GB * 0.023)

def onprem(gb, lp=1.0, fx=PHP_PER_USD):
    electricity = 8 * 0.045 * 8 * 30 * 14.35          # PHP per month
    hardware = 69995 * 8 / 60
    maintenance = 3500
    lost_productivity = 13952 * lp                     # 2 h x 8 engineers x PHP 218 x 4 weeks
    scale = 1 + max(0, (gb - 500) / 5000)              # +1% per 50 GB above 500 GB
    return (hardware + electricity + maintenance + lost_productivity) * scale / fx

def run(lp=1.0, fx=PHP_PER_USD, mig_mult=1.0, glue_kw=None, adf_kw=None, df_kw=None, df_cost_mult=1.0):
    fns = {'AWS Glue':     lambda g, j: glue(g, j, **(glue_kw or {})),
           'Azure ADF':    lambda g, j: adf(g, j, **(adf_kw or {})),
           'GCP Dataflow': lambda g, j: dataflow(g, j, **(df_kw or {})) * df_cost_mult}
    cum_cloud = {p: MIGRATION[p] * mig_mult + fns[p](BASE_GB, BASE_JOBS) * STAGING_SHARE * STAGING_MONTHS for p in fns}
    cum_onprem, breakeven = 0.0, {p: None for p in fns}
    for m in range(1, HORIZON + 1):
        s = GROWTH ** ((m - 1) // 12)
        gb, jobs = BASE_GB * s, int(BASE_JOBS * s)
        cum_onprem += onprem(gb, lp, fx)
        for p in fns:
            cum_cloud[p] += fns[p](gb, jobs) + SECONDARY[p]
            if breakeven[p] is None and cum_cloud[p] < cum_onprem:
                breakeven[p] = m
    return {'breakeven': breakeven,
            'net36': {p: round(cum_onprem - cum_cloud[p]) for p in fns},
            'monthly': {p: round(fns[p](BASE_GB, BASE_JOBS) + SECONDARY[p], 2) for p in fns},
            'onprem_monthly': round(onprem(BASE_GB, lp, fx), 2)}

# ------------------- check the baseline against the published numbers -----------
b = run()
assert b['monthly'] == {'AWS Glue': 154.14, 'Azure ADF': 488.60, 'GCP Dataflow': 63.58}, b['monthly']
assert b['onprem_monthly'] == 474.99, b['onprem_monthly']
assert b['breakeven'] == {'AWS Glue': 14, 'Azure ADF': None, 'GCP Dataflow': 11}, b['breakeven']
assert b['net36'] == {'AWS Glue': 6517, 'Azure ADF': -8318, 'GCP Dataflow': 10605}, b['net36']
print('Baseline reproduces the published results.')

# --------------------------------- Table 7 --------------------------------------
CASES = [
    ('Baseline',                         {}),
    ('Lost productivity 0%',             dict(lp=0.0)),
    ('Lost productivity 50%',            dict(lp=0.5)),
    ('Lost productivity 150%',           dict(lp=1.5)),
    ('ADF Data Flow at 4 vCores',        dict(adf_kw={'vcores': 4})),
    ('Glue Flex pricing ($0.29/DPU-h)',  dict(glue_kw={'rate': 0.29})),
    ('Job duration 15 min',              dict(glue_kw={'dur': .25}, adf_kw={'dur': .25}, df_kw={'dur': .25})),
    ('Job duration 60 min',              dict(glue_kw={'dur': 1.0}, adf_kw={'dur': 1.0}, df_kw={'dur': 1.0})),
    ('Job duration 120 min',             dict(glue_kw={'dur': 2.0}, adf_kw={'dur': 2.0}, df_kw={'dur': 2.0})),
    ('Exchange rate PHP 63.28/USD',      dict(fx=63.28)),
    ('Migration cost +50%',              dict(mig_mult=1.5)),
    ('Migration cost +100%',             dict(mig_mult=2.0)),
]
def fmt(r, p):
    be = r['breakeven'][p]
    return f"{be if be else 'none'} / {r['net36'][p]:,}"
rows = []
for name, kw in CASES:
    r = run(**kw)
    rows.append({'Case': name, **{p: fmt(r, p) for p in ('AWS Glue', 'Azure ADF', 'GCP Dataflow')}})
table7 = pd.DataFrame(rows)
print('\nTable 7 - break-even month / 36-month net saving (USD)\n', table7.to_string(index=False))

# ------------- lost-productivity share needed for a positive 36-month saving ------
def bisect(f, lo, hi, n=50):
    for _ in range(n):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if f(mid) else (mid, hi)
    return hi
print('\nLost productivity (as share of the assumed value) at which the 36-month net saving reaches zero:')
for p in ('AWS Glue', 'Azure ADF'):
    print(f'  {p:12s} {bisect(lambda x: run(lp=x)["net36"][p] > 0, 0, 5):.2f}')

# ------------- Dataflow usage-cost multiplier the result can absorb ----------------
print('\nDataflow monthly cost at which the 36-month net saving reaches zero (usage cost scaled, secondary costs fixed):')
for lp in (1.0, 0.0):
    mult = bisect(lambda x: run(lp=lp, df_cost_mult=x)['net36']['GCP Dataflow'] < 0, 1, 100)
    monthly = dataflow(BASE_GB, BASE_JOBS) * mult + SECONDARY['GCP Dataflow']
    print(f'  lost productivity {lp:.0%}: about ${monthly:,.0f} per month '
          f'({monthly / b["monthly"]["GCP Dataflow"]:.1f} times the modeled ${b["monthly"]["GCP Dataflow"]})')

os.makedirs('outputs', exist_ok=True)
table7.to_csv('outputs/table7_cost_sensitivity.csv', index=False)
print('\nSaved outputs/table7_cost_sensitivity.csv')
