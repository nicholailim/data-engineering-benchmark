"""
02_cloud_cost_model.py (Sections 3.2, 3.3, 4.3-4.5)
Original cost, TCO, ROI and weighted-scoring model (unchanged from the version used for the
results in the paper; provider rates as of April 2025, PHP 59.00 per USD).  Run from the
repository root:  python scripts/02_cloud_cost_model.py
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

os.makedirs('outputs', exist_ok=True)

# ════════════════════════════════════════════════════════════
# WORKLOAD ASSUMPTIONS
# Representative parameters for an 8-person BPO analytics
# team running internal reporting pipelines on laptops.
# All assumptions documented in Appendix.
# ════════════════════════════════════════════════════════════
WORKLOAD = {
    'low'      : {'label': 'Low (250 GB)',      'gb': 250,  'jobs': 150},
    'baseline' : {'label': 'Baseline (500 GB)', 'gb': 500,  'jobs': 300},
    'high'     : {'label': 'High (1 TB)',        'gb': 1000, 'jobs': 600},
}

JOB_DURATION_HRS = 0.5    # 30 minutes average per ETL job
STORAGE_GB       = 100    # output and staging storage
PHP_PER_USD      = 59.0   # exchange rate April 2025

# ════════════════════════════════════════════════════════════
# SECONDARY MONTHLY COSTS
# Verified from official vendor documentation, April 2025
# These are added on top of primary compute costs
# ════════════════════════════════════════════════════════════
SECONDARY_COSTS = {
    # Monitoring and logging
    # AWS CloudWatch: ~$3-5/month at this scale
    # ADF Monitor: ~$2-4/month
    # GCP Cloud Monitoring: free up to 50GB logs/month
    'monitoring': {
        'AWS Glue'    : 4.0,
        'Azure ADF'   : 3.0,
        'GCP Dataflow': 0.0,
    },
    # Network egress (data leaving cloud region)
    # ~100GB output data at Singapore region rates
    # AWS: $0.09/GB, Azure: $0.087/GB, GCP: $0.08/GB
    'network': {
        'AWS Glue'    : 9.0,
        'Azure ADF'   : 8.7,
        'GCP Dataflow': 8.0,
    },
    # Secrets management (credentials, API keys)
    # AWS Secrets Manager: $0.40/secret x 10 secrets
    # Azure Key Vault: ~$0.03/10k operations
    # GCP Secret Manager: $0.06/secret x 10 secrets
    'security': {
        'AWS Glue'    : 4.0,
        'Azure ADF'   : 3.0,
        'GCP Dataflow': 0.6,
    },
    # Basic support tier (free for all platforms at this scale)
    'support': {
        'AWS Glue'    : 0.0,
        'Azure ADF'   : 0.0,
        'GCP Dataflow': 0.0,
    },
}

def total_secondary(platform):
    """Sum all secondary monthly costs for a given platform."""
    return sum(
        costs[platform]
        for costs in SECONDARY_COSTS.values()
    )

# ════════════════════════════════════════════════════════════
# ONE-TIME MIGRATION COSTS
# Based on Philippine IT labor rates and published benchmarks
# for small-team ETL migrations (6-8 week timeline)
# Source: Entrans.ai (2025), Caliberfocus (2026)
# ════════════════════════════════════════════════════════════
MIGRATION_COSTS = {
    # Breakdown (PHP → USD at 59.0):
    # Pipeline redesign & setup  : PHP 100,000 (~$1,754)
    # Initial data migration      : PHP 25,000  (~$439)
    # Testing & validation        : PHP 50,000  (~$877)
    # Team training & upskilling  : PHP 40,000  (~$702)
    # Documentation & change mgmt : PHP 20,000  (~$351)
    # Platform-specific setup     : varies
    'AWS Glue'    : 4200,   # slightly higher: IAM + Spark learning curve
    'Azure ADF'   : 4000,   # visual designer reduces setup time
    'GCP Dataflow': 4100,   # Apache Beam learning curve
}

# Staging/test environment cost (first 6 months only)
# Running at 20% of production workload during parallel testing
STAGING_MONTHS  = 6
STAGING_FACTOR  = 0.20

# ════════════════════════════════════════════════════════════
# PRIMARY PRICING FUNCTIONS
# All rates verified from official pricing pages, April 2025
# Region: Singapore (asia-southeast1 / ap-southeast-1)
# ════════════════════════════════════════════════════════════

def cost_aws_glue(gb, jobs):
    """
    AWS Glue — ap-southeast-1 (Singapore)
    Source: aws.amazon.com/glue/pricing

    ETL Jobs  : $0.44/DPU-hour, min 2 DPUs per job
    Crawlers  : $0.44/DPU-hour, 2 DPUs, ~6 min per run
                1 crawler per 10 ETL jobs assumed
    S3 Storage: $0.025/GB-month
    Data Catalog: First 1M objects free (no charge at this scale)

    Note: Flex execution ($0.29/DPU-hour) available for
    non-urgent batch jobs — represents a 34% cost reduction
    opportunity not modeled in primary scenario (conservative).
    """
    etl_cost     = 2 * JOB_DURATION_HRS * jobs * 0.44
    crawler_runs = jobs / 10
    crawler_cost = crawler_runs * 2 * (6/60) * 0.44
    storage_cost = STORAGE_GB * 0.025
    return round(etl_cost + crawler_cost + storage_cost, 2)

def cost_azure_adf(gb, jobs):
    """
    Azure Data Factory — Southeast Asia region
    Source: azure.microsoft.com/pricing/details/data-factory

    Orchestration : $1.00 per 1,000 pipeline runs (Azure IR)
    Data Movement : 4 DIUs x 15min x 2 copy activities x $0.25/DIU-hour
    Data Flows    : Minimum 8 vCores (Microsoft requirement)
                    $0.268/vCore-hour, 30 min per job
    Storage       : Azure Blob $0.02/GB-month

    Note: ADF Data Flows enforce minimum 8-vCore configuration,
    making it expensive for frequent small jobs. A 4-vCore
    configuration would reduce cost to ~$158/month but with
    reduced transformation capacity.
    """
    orch_cost     = (jobs / 1000) * 1.00
    diu_hours     = jobs * 2 * (15/60) * 4
    movement_cost = diu_hours * 0.25
    vcore_hours   = jobs * (30/60) * 8
    dataflow_cost = vcore_hours * 0.268
    storage_cost  = STORAGE_GB * 0.02
    return round(orch_cost + movement_cost + dataflow_cost
                 + storage_cost, 2)

def cost_gcp_dataflow(gb, jobs):
    """
    GCP Dataflow — asia-southeast1 (Singapore), Batch mode
    Source: cloud.google.com/dataflow/pricing
    Rates verified from official pricing page, April 2025

    vCPU    : $0.07/vCPU-hour  (n1-standard-4, 4 vCPUs)
    Memory  : $0.0044463/GB-hour (15 GB per job)
    Shuffle : $0.01357/GB processed (est. 10% of input volume)
    Storage : GCS Standard $0.023/GB-month
    """
    vcpu_cost    = 4 * JOB_DURATION_HRS * jobs * 0.07
    memory_cost  = 15 * JOB_DURATION_HRS * jobs * 0.0044463
    shuffle_gb   = gb * 0.10
    shuffle_cost = shuffle_gb * 0.01357
    storage_cost = STORAGE_GB * 0.023
    return round(vcpu_cost + memory_cost + shuffle_cost
                 + storage_cost, 2)

def cost_on_premise(gb, jobs):
    """
    On-premise laptop-based environment (PHP → USD)
    8 ThinkPad laptops, Python ETL scripts via VS Code

    Hardware depreciation : 8 x PHP 60,000 / 60 months = PHP 8,000
    Electricity           : 8 x 45W x 8hrs x 30d x PHP10/kWh = PHP 864
    IT maintenance        : PHP 3,500 (environment troubleshooting)
    Lost productivity     : 2hrs/engineer/week x 8 x PHP218/hr = PHP 13,952
    Software licensing    : PHP 0 (Python + VS Code open source)

    Scales with data volume: higher GB = more delay hours observed
    """
    electricity = 8 * 0.045 * 8 * 30 * 14.35
    hardware = (69995 * 8) / 60 
    base_php = hardware + electricity + 3500 + 13952
    scale    = 1 + max(0, (gb - 500) / 5000)
    return round((base_php * scale) / PHP_PER_USD, 2)

# ════════════════════════════════════════════════════════════
# ANALYSIS 1 — THREE-SCENARIO COST SIMULATION
# Primary costs only (for transparent comparison)
# Secondary costs shown separately for methodological clarity
# ════════════════════════════════════════════════════════════
platforms = ['AWS Glue', 'Azure ADF', 'GCP Dataflow']

results_primary  = []
results_revised  = []

for scenario, params in WORKLOAD.items():
    gb, jobs = params['gb'], params['jobs']
    row_p = {'Scenario': params['label'],
             'On-Premise': cost_on_premise(gb, jobs)}
    row_r = {'Scenario': params['label'],
             'On-Premise': cost_on_premise(gb, jobs)}
    for p in platforms:
        primary = {'AWS Glue'    : cost_aws_glue,
                   'Azure ADF'   : cost_azure_adf,
                   'GCP Dataflow': cost_gcp_dataflow}[p](gb, jobs)
        secondary  = total_secondary(p)
        staging    = primary * STAGING_FACTOR  # only first 6 months
        row_p[p]   = primary
        row_r[p]   = round(primary + secondary, 2)
    results_primary.append(row_p)
    results_revised.append(row_r)

df_primary = pd.DataFrame(results_primary)
df_revised = pd.DataFrame(results_revised)

print("=" * 70)
print("ANALYSIS 1A: PRIMARY COSTS ONLY (Monthly USD)")
print("=" * 70)
print(df_primary.to_string(index=False))

print("\n" + "=" * 70)
print("ANALYSIS 1B: REVISED COSTS (Primary + Secondary, Monthly USD)")
print("=" * 70)
print(df_revised.to_string(index=False))

print("\nSecondary cost breakdown per platform (monthly USD):")
for p in platforms:
    sec = total_secondary(p)
    print(f"  {p:<15}: ${sec:.2f}/month")
    for cat, costs in SECONDARY_COSTS.items():
        if costs[p] > 0:
            print(f"    {cat:<12}: ${costs[p]:.2f}")

# Platform ranking check
print("\nPlatform ranking (revised costs, cheapest → most expensive):")
prev_rank = None
ranking_changes = False
for _, row in df_revised.iterrows():
    ranked = sorted(platforms, key=lambda p: row[p])
    print(f"  {row['Scenario']:<22}: {' < '.join(ranked)}")
    if prev_rank and ranked != prev_rank:
        ranking_changes = True
    prev_rank = ranked

if ranking_changes:
    print("\n  *** FINDING: Ranking CHANGES across scenarios.")
else:
    print("\n  *** FINDING: Ranking CONSISTENT — recommendation "
          "is robust to workload variation.")

# Monthly savings vs on-premise (revised baseline)
baseline_r = df_revised[
    df_revised['Scenario'] == 'Baseline (500 GB)'
].iloc[0]
print(f"\nRevised monthly savings vs on-premise (baseline):")
for p in platforms:
    saving     = baseline_r['On-Premise'] - baseline_r[p]
    saving_pct = (saving / baseline_r['On-Premise']) * 100
    direction  = 'saved' if saving > 0 else 'MORE expensive'
    print(f"  {p:<15}: ${abs(saving):>7.2f}/month "
          f"{direction} ({abs(saving_pct):.1f}%)")

# ════════════════════════════════════════════════════════════
# FIGURE 7 — Grouped Bar Chart: Primary vs Revised Costs
# Side-by-side shows impact of secondary costs transparently
# ════════════════════════════════════════════════════════════
COLORS = {
    'On-Premise'  : '#6B7C93',
    'AWS Glue'    : '#E8A020',
    'Azure ADF'   : '#2E6DA4',
    'GCP Dataflow': '#27AE60',
}
all_cols = ['On-Premise'] + platforms
x        = np.arange(len(df_primary))
width    = 0.18

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

for ax, df, title_suffix in zip(
        axes,
        [df_primary, df_revised],
        ['Primary Costs Only', 'Revised (+ Secondary Costs)']):
    for i, col in enumerate(all_cols):
        offset = (i - 1.5) * width
        bars   = ax.bar(x + offset, df[col], width,
                        label=col, color=COLORS[col],
                        edgecolor='white', linewidth=0.5)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2,
                    h + 2, f'${h:.0f}',
                    ha='center', va='bottom',
                    fontsize=7, color='#444')
    ax.set_xticks(x)
    ax.set_xticklabels(df['Scenario'], fontsize=9)
    ax.set_ylabel('Estimated Monthly Cost (USD)', fontsize=10)
    ax.set_title(title_suffix, fontsize=11, fontweight='bold')
    ax.legend(fontsize=8.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylim(0, df[all_cols].values.max() * 1.22)

plt.suptitle(
    'Figure 7. Monthly Cost Comparison by Workload Scenario\n'
    'On-Premise vs Cloud ETL Platforms — Singapore Region, April 2025',
    fontsize=12, fontweight='bold', y=1.02
)
plt.tight_layout()
plt.savefig('outputs/fig7_cost_scenarios.png',
            bbox_inches='tight', dpi=150)
plt.close()
print("\nFigure 7 saved.")

# ════════════════════════════════════════════════════════════
# ANALYSIS 2 — 3-YEAR TCO WITH REVISED COSTS + GROWTH
# Uses revised (primary + secondary) monthly costs
# Migration cost includes staging environment for first 6 months
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 2: 3-YEAR TCO PROJECTION")
print("(Revised monthly costs + 20% annual data growth)")
print("=" * 70)

months      = 36
growth_rate = 0.20
base_gb     = 500
base_jobs   = 300

# Full migration cost = one-time + staging environment cost
def full_migration_cost(platform):
    primary_baseline = {'AWS Glue'    : cost_aws_glue,
                        'Azure ADF'   : cost_azure_adf,
                        'GCP Dataflow': cost_gcp_dataflow
                        }[platform](base_gb, base_jobs)
    staging_total = (primary_baseline * STAGING_FACTOR
                     * STAGING_MONTHS)
    return MIGRATION_COSTS[platform] + staging_total

print("\nFull migration cost (one-time + staging):")
for p in platforms:
    fmc = full_migration_cost(p)
    print(f"  {p:<15}: ${fmc:,.0f}  "
          f"(one-time: ${MIGRATION_COSTS[p]:,} + "
          f"staging: ${fmc-MIGRATION_COSTS[p]:,.0f})")

# Build TCO
cumulative   = {'On-Premise': 0}
for p in platforms:
    cumulative[p] = full_migration_cost(p)

tco_records = []
for m in range(1, months + 1):
    year_idx = (m - 1) // 12
    scale    = (1 + growth_rate) ** year_idx
    gb_m     = base_gb  * scale
    jobs_m   = int(base_jobs * scale)

    cumulative['On-Premise'] += cost_on_premise(gb_m, jobs_m)
    for p in platforms:
        primary   = {'AWS Glue'    : cost_aws_glue,
                     'Azure ADF'   : cost_azure_adf,
                     'GCP Dataflow': cost_gcp_dataflow
                     }[p](gb_m, jobs_m)
        secondary = total_secondary(p)
        cumulative[p] += (primary + secondary)

    tco_records.append({**{'Month': m}, **dict(cumulative)})

df_tco = pd.DataFrame(tco_records)

print(f"\nCumulative 3-Year TCO (revised model):")
for col in ['On-Premise'] + platforms:
    total     = df_tco[col].iloc[-1]
    total_php = total * PHP_PER_USD
    print(f"  {col:<15}: ${total:>8,.0f}  "
          f"(₱{total_php:>10,.0f})")

# ── FIGURE 8 — TCO Line Chart ────────────────────────────────
TCO_COLORS = {
    'On-Premise'  : '#6B7C93',
    'AWS Glue'    : '#E8A020',
    'Azure ADF'   : '#2E6DA4',
    'GCP Dataflow': '#27AE60',
}
fig, ax = plt.subplots(figsize=(12, 6))
for col, color in TCO_COLORS.items():
    style = '--' if col == 'On-Premise' else '-'
    ax.plot(df_tco['Month'], df_tco[col],
            label=col, color=color,
            linewidth=2.2, linestyle=style)

# Year markers
for yr, label in [(12, 'Year 2'), (24, 'Year 3')]:
    ax.axvline(yr, color='gray', linestyle=':',
               alpha=0.5, linewidth=1)
    ax.text(yr + 0.3,
            df_tco['On-Premise'].max() * 0.08,
            label, fontsize=8.5, color='gray')

ax.set_xlabel('Month', fontsize=11)
ax.set_ylabel('Cumulative Cost (USD)', fontsize=11)
ax.set_title(
    'Figure 8. 3-Year Total Cost of Ownership Projection\n'
    '(Revised model: primary + secondary costs; '
    '20% annual data growth)',
    fontsize=12, fontweight='bold', pad=12
)
ax.legend(fontsize=9.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.yaxis.set_major_formatter(
    plt.FuncFormatter(lambda v, _: f'${v:,.0f}')
)
plt.tight_layout()
plt.savefig('outputs/fig8_tco_projection.png',
            bbox_inches='tight', dpi=150)
plt.close()
print("Figure 8 saved.")

# ════════════════════════════════════════════════════════════
# ANALYSIS 3 — BREAK-EVEN (REVISED MODEL)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 3: BREAK-EVEN ANALYSIS (Revised Model)")
print("=" * 70)

for p in platforms:
    be_month = None
    for _, row in df_tco.iterrows():
        if row[p] < row['On-Premise']:
            be_month = int(row['Month'])
            break
    saving_36 = df_tco['On-Premise'].iloc[-1] - df_tco[p].iloc[-1]
    saving_php = saving_36 * PHP_PER_USD
    if be_month:
        print(f"  {p:<15}: break-even month {be_month:>2}  |  "
              f"3-yr net saving: ${saving_36:>8,.0f}  "
              f"(₱{saving_php:>10,.0f})")
    else:
        print(f"  {p:<15}: no break-even within 36 months  |  "
              f"3-yr net LOSS: ${abs(saving_36):>8,.0f}  "
              f"(₱{abs(saving_php):>10,.0f})")

print("\nComparison: Original vs Revised break-even:")
print("  Platform        Original   Revised    Difference")
print("  " + "-" * 50)
original_be = {'AWS Glue': 9, 'Azure ADF': None, 'GCP Dataflow': 6}
for p in platforms:
    be_month = None
    for _, row in df_tco.iterrows():
        if row[p] < row['On-Premise']:
            be_month = int(row['Month'])
            break
    orig = str(original_be[p]) if original_be[p] else 'N/A'
    rev  = str(be_month) if be_month else 'N/A'
    diff = (f"+{be_month - original_be[p]} months"
            if be_month and original_be[p] else '—')
    print(f"  {p:<15} {orig:>8}   {rev:>7}   {diff}")

# ════════════════════════════════════════════════════════════
# ANALYSIS 4 — WEIGHTED SCORING MATRIX (UNCHANGED)
# Scoring is qualitative — not affected by cost revision
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 4: WEIGHTED MULTI-CRITERIA SCORING MATRIX")
print("=" * 70)

CRITERIA = {
    'Cost Efficiency'      : 0.30,
    'Scalability'          : 0.20,
    'Migration Complexity' : 0.25,
    'Vendor Lock-in Risk'  : 0.15,
    'Sustainability'       : 0.10,
}
RAW_SCORES = {
    'AWS Glue'    : [4, 5, 3, 2, 4],
    'Azure ADF'   : [3, 4, 4, 2, 4],
    'GCP Dataflow': [5, 4, 3, 3, 5],
}
weights  = list(CRITERIA.values())
criteria = list(CRITERIA.keys())

print(f"\n  {'Criterion':<25} {'Weight':>7}  "
      f"{'AWS Glue':>9}  {'Azure ADF':>9}  {'GCP':>9}")
print("  " + "-" * 62)
for i, (criterion, weight) in enumerate(CRITERIA.items()):
    print(f"  {criterion:<25} {weight:>6.0%}  "
          f"{RAW_SCORES['AWS Glue'][i]:>9}  "
          f"{RAW_SCORES['Azure ADF'][i]:>9}  "
          f"{RAW_SCORES['GCP Dataflow'][i]:>9}")

weighted = {p: round(sum(s * w for s, w in
            zip(RAW_SCORES[p], weights)), 3)
            for p in platforms}
print(f"\n  {'WEIGHTED TOTAL':<25} {'':>7}  "
      f"{weighted['AWS Glue']:>9.3f}  "
      f"{weighted['Azure ADF']:>9.3f}  "
      f"{weighted['GCP Dataflow']:>9.3f}")
print(f"\n  RECOMMENDED: GCP Dataflow "
      f"(score: {weighted['GCP Dataflow']:.3f} / 5.000)")

# ── FIGURE 9 — Weighted Score Charts ─────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
x = np.arange(len(criteria))
w = 0.25
ax = axes[0]
for i, (p, color) in enumerate(zip(platforms,
        ['#E8A020', '#2E6DA4', '#27AE60'])):
    bars = ax.bar(x + (i-1)*w, RAW_SCORES[p], w,
                  label=p, color=color,
                  edgecolor='white', linewidth=0.5)
ax.set_xticks(x)
ax.set_xticklabels(criteria, rotation=20, ha='right', fontsize=9)
ax.set_ylabel('Raw Score (1–5)', fontsize=10)
ax.set_title('Raw Scores by Criterion', fontsize=11,
             fontweight='bold')
ax.set_ylim(0, 6.5)
ax.legend(fontsize=9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

ax2     = axes[1]
scores  = list(weighted.values())
colors  = ['#E8A020', '#2E6DA4', '#27AE60']
bars    = ax2.bar(list(weighted.keys()), scores,
                  color=colors, edgecolor='white', width=0.5)
for bar, score in zip(bars, scores):
    ax2.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.05,
             f'{score:.3f}', ha='center',
             fontsize=11, fontweight='bold')
ax2.set_ylabel('Weighted Score (out of 5.0)', fontsize=10)
ax2.set_title('Final Weighted Composite Scores',
              fontsize=11, fontweight='bold')
ax2.set_ylim(0, max(scores) * 1.25)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

plt.suptitle(
    'Figure 9. Multi-Criteria Weighted Scoring Matrix\n'
    'Cloud ETL Platform Evaluation for Company X',
    fontsize=12, fontweight='bold', y=1.02
)
plt.tight_layout()
plt.savefig('outputs/fig9_weighted_scoring.png',
            bbox_inches='tight', dpi=150)
plt.close()
print("Figure 9 saved.")

# ════════════════════════════════════════════════════════════
# ANALYSIS 5 — SENSITIVITY ANALYSIS
# Tests ROI robustness when workload assumptions vary ±50%
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 5: SENSITIVITY ANALYSIS — REVISED MODEL")
print("=" * 70)

VOLUME_VARIATIONS = [0.50, 0.75, 1.00, 1.25, 1.50]

print(f"\n  Annual ROI (%) — revised costs, by workload multiplier:")
print(f"  {'Platform':<15} " +
      "  ".join(f"{int(v*100)}% vol" for v in VOLUME_VARIATIONS))
print("  " + "-" * 68)

sensitivity_rows = []
for p in platforms:
    row_vals = []
    for v in VOLUME_VARIATIONS:
        gb_v    = base_gb  * v
        jobs_v  = int(base_jobs * v)
        primary = {'AWS Glue'    : cost_aws_glue,
                   'Azure ADF'   : cost_azure_adf,
                   'GCP Dataflow': cost_gcp_dataflow
                   }[p](gb_v, jobs_v)
        cloud_m  = primary + total_secondary(p)
        onprem_m = cost_on_premise(gb_v, jobs_v)
        annual_saving = (onprem_m - cloud_m) * 12
        fmc           = full_migration_cost(p)
        roi           = (annual_saving - fmc) / fmc * 100
        row_vals.append(round(roi, 1))
    sensitivity_rows.append(
        {'Platform': p,
         **dict(zip([int(v*100) for v in VOLUME_VARIATIONS],
                    row_vals))}
    )
    print(f"  {p:<15} " +
          "  ".join(f"{v:>8.1f}%" for v in row_vals))

df_sensitivity = pd.DataFrame(sensitivity_rows)

# Check if GCP stays positive at all volume levels
gcp_row = df_sensitivity[
    df_sensitivity['Platform'] == 'GCP Dataflow'
].iloc[0]
all_positive = all(
    gcp_row[int(v*100)] > 0 for v in VOLUME_VARIATIONS
)
print(f"\n  GCP Dataflow ROI positive at all volume levels: "
      f"{'YES — robust recommendation' if all_positive else 'NO'}")

# ── FIGURE 10 — Sensitivity Chart ────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6))
vol_labels = [f'{int(v*100)}%' for v in VOLUME_VARIATIONS]

for p, color in zip(platforms,
        ['#E8A020', '#2E6DA4', '#27AE60']):
    row  = df_sensitivity[df_sensitivity['Platform'] == p].iloc[0]
    vals = [row[int(v*100)] for v in VOLUME_VARIATIONS]
    ax.plot(vol_labels, vals, marker='o',
            label=p, color=color,
            linewidth=2.2, markersize=7)
    for x_pt, y_pt in zip(vol_labels, vals):
        ax.annotate(f'{y_pt:.1f}%',
                    (x_pt, y_pt),
                    textcoords='offset points',
                    xytext=(0, 9),
                    ha='center', fontsize=8.5, color=color)

ax.axhline(0, color='red', linestyle='--',
           alpha=0.4, linewidth=1.2)
ax.text(4.05, 3, 'Break-even (ROI = 0)',
        fontsize=8.5, color='red', alpha=0.7)
ax.set_xlabel(
    'Workload Volume (% of Baseline 500 GB/month)',
    fontsize=11
)
ax.set_ylabel('First-Year ROI (%)', fontsize=11)
ax.set_title(
    'Figure 10. Sensitivity Analysis — First-Year ROI '
    'Under Varying Workload Assumptions\n'
    '(Revised model with secondary costs and full '
    'migration cost; dashed line = break-even)',
    fontsize=11, fontweight='bold', pad=12
)
ax.legend(fontsize=9.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig('outputs/fig10_sensitivity.png',
            bbox_inches='tight', dpi=150)
plt.close()
print("Figure 10 saved.")

# ════════════════════════════════════════════════════════════
# FINAL SUMMARY — KEY NUMBERS FOR CHAPTER 4.2
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("KEY NUMBERS FOR CHAPTER 4.2 (REVISED MODEL)")
print("=" * 70)

onprem_36 = df_tco['On-Premise'].iloc[-1]
base_op   = cost_on_premise(500, 300)

for p in platforms:
    cloud_36   = df_tco[p].iloc[-1]
    net_saving = onprem_36 - cloud_36
    net_php    = net_saving * PHP_PER_USD
    primary_m  = {'AWS Glue'    : cost_aws_glue,
                  'Azure ADF'   : cost_azure_adf,
                  'GCP Dataflow': cost_gcp_dataflow
                  }[p](500, 300)
    revised_m  = primary_m + total_secondary(p)
    saving_m   = base_op - revised_m
    saving_pct = (saving_m / base_op) * 100
    be_month   = None
    for _, row in df_tco.iterrows():
        if row[p] < row['On-Premise']:
            be_month = int(row['Month'])
            break
    fmc = full_migration_cost(p)

    print(f"\n{p}")
    print(f"  Primary monthly cost         : ${primary_m:.2f}")
    print(f"  Secondary monthly cost       : ${total_secondary(p):.2f}")
    print(f"  Revised monthly cost         : ${revised_m:.2f}")
    print(f"  Monthly saving vs on-premise : "
          f"${saving_m:.2f} ({saving_pct:.1f}%)")
    print(f"  Full migration cost          : ${fmc:,.0f} "
          f"(₱{fmc*PHP_PER_USD:,.0f})")
    print(f"  Break-even month             : "
          f"{be_month if be_month else 'No break-even'}")
    print(f"  3-year net saving (USD)      : ${net_saving:,.0f}")
    print(f"  3-year net saving (PHP)      : ₱{net_php:,.0f}")

# ── Export tables ─────────────────────────────────────────────
df_primary.to_csv('outputs/table_costs_primary.csv', index=False)
df_revised.to_csv('outputs/table_costs_revised.csv', index=False)
df_tco[['Month', 'On-Premise'] + platforms]\
    .to_csv('outputs/table_tco.csv', index=False)
df_sensitivity.to_csv('outputs/table_sensitivity.csv', index=False)

print("\n" + "=" * 70)
print("WEEK 2 COMPLETE — Figures 7–10 and 4 tables saved.")
print("=" * 70)