"""
01_extract_and_benchmark.py (Section 3.1, 4.1, 4.2, Fig. 1)
Filters data-engineering postings, extracts the 37-technology dictionary with regular
expressions, and produces the benchmark tables and figures.  Revised patterns: aliases
such as "lambda", "glue", "dataflow", "big query", "air flow", "cicd", "ML"; a guard for
"Spark Capital"; deterministic tie-breaking.  Reads data/clean_jobs.csv (not included,
see data/README.md).  Run from the repository root:  python scripts/01_extract_and_benchmark.py
"""
import pandas as pd
import re
import os
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

# LOAD DATA

df_raw = pd.read_csv('data/clean_jobs.csv')
print(f"Raw dataset: {len(df_raw)} rows")

# FILTERING DATA ENGINEERING ROLES

DE_KEYWORDS = [
    'data engineer',
    'etl',
    'data pipeline',
    'analytics engineer',
    'data integration',
    'data platform',
    'data infrastructure',
    'pipeline engineer',
]

def is_data_engineering_role(title):
    title_lower = str(title).lower()
    return any(keyword in title_lower for keyword in DE_KEYWORDS)

df_de = df_raw[df_raw['title'].apply(is_data_engineering_role)].copy()
print(f"After role filter: {len(df_de)} rows")

df_de = df_de.drop_duplicates(subset=['description'])
print(f"After removing duplicates: {len(df_de)} rows")

df_de = df_de.dropna(subset=['description'])
df_de['description'] = df_de['description'].astype(str)
print(f"Final Clean Dataset: {len(df_de)} rows")

print("\nRoles included in analysis:")
print(df_de['title'].value_counts().head(15).to_string())

# TECHNOLOGY DICTIONARY

TECH_DICT = {
    # Programming Languages
    'Python': [r'\bpython\b'],
    'SQL': [r'\bsql\b', r'\bt-sql\b', r'\bpl/sql\b'],
    'Scala': [r'\bscala\b'],
    'Java': [r'\bjava\b(?!script)'],
    'Bash/Shell': [r'\bbash\b', r'\bshell script'],

    # Cloud Platforms
    'AWS': [r'\baws\b', r'amazon web services', r'amazon s3', r'amazon redshift'],
    'Azure': [r'\bazure\b', r'microsoft azure', r'azure data factory', r'azure synapse'],
    'GCP': [r'\bgcp\b', r'google cloud', r'bigquery', r'google cloud platform'],

    # ETL / ELT Tools
    'AWS Glue': [r'aws glue', r'amazon glue', r'\bglue\b'],
    'Azure Data Factory': [r'azure data factory', r'\badf\b'],
    'GCP Dataflow': [r'cloud dataflow', r'google dataflow', r'\bdataflow\b'],
    'dbt': [r'\bdbt\b', r'data build tool'],
    'Informatica': [r'informatica'],
    'Talend': [r'\btalend\b'],
    'Fivetran': [r'\bfivetran\b'],
    'Airbyte': [r'\bairbyte\b'],

    # Orchestration
    'Apache Airflow': [r'\bairflow\b', r'apache airflow', r'air flow', r'cloud composer'],
    'Prefect': [r'\bprefect\b'],
    'Dagster': [r'\bdagster\b'],

    # Processing Frameworks
    'Apache Spark': [r'\bspark\b(?!\s+capital)', r'apache spark', r'pyspark'],
    'Apache Kafka': [r'\bkafka\b', r'apache kafka'],
    'Apache Flink': [r'\bflink\b', r'apache flink'],
    'Apache Hadoop': [r'\bhadoop\b', r'hdfs', r'\bhive\b', r'hiveql'],
    'Databricks': [r'\bdatabricks\b'],

    # Data Warehouses
    'Snowflake': [r'\bsnowflake\b'],
    'Redshift': [r'\bredshift\b'],
    'BigQuery': [r'\bbigquery\b', r'big query'],
    'PostgreSQL': [r'\bpostgresql\b', r'\bpostgres\b'],

    # DevOps / Containerization
    'Docker': [r'\bdocker\b'],
    'Kubernetes': [r'\bkubernetes\b', r'\bk8s\b'],
    'Terraform': [r'\bterraform\b'],
    'CI/CD': [r'\bci/cd\b', r'github actions', r'jenkins', r'\bcicd\b', r'ci\s*-\s*cd', r'continuous (integration|deployment)'],

    # Modern / AI
    'Serverless': [r'\bserverless\b', r'aws lambda', r'azure functions', r'cloud functions', r'\blambda\b', r'cloud run', r'step functions', r'function apps?\b'],
    'Machine Learning': [r'\bmachine learning\b', r'\bmlops\b', r'\bml\b'],

    # BI / Visualization
    'Tableau': [r'\btableau\b'],
    'Power BI': [r'power bi', r'\bpowerbi\b'],
    'Looker': [r'\blooker\b'],
}

def extract_technologies(text):
    text_lower = str(text).lower()
    detected = set()
    for canonical_name, patterns in TECH_DICT.items():
        if any(re.search(pattern, text_lower) for pattern in patterns):
            detected.add(canonical_name)
    return detected

df_de['technologies'] = df_de['description'].apply(extract_technologies)
df_de['tech_count'] = df_de['technologies'].apply(len)

print(f"Avg technologies per posting: {df_de['tech_count'].mean():.1f}")
print(f"Max technologies in one posting: {df_de['tech_count'].max()}")
print(f"Postings with at least 1 technology: {(df_de['tech_count'] > 0).sum()}")

print("\nSample - technologies found in first 3 postings:")
for i, row in df_de.head(3).iterrows():
    print(f"  [{row['title']}]")
    print(f"  Found: {sorted(row['technologies'])}")
    print()

# =========================
# OUTPUT FOLDER
# =========================
os.makedirs('outputs', exist_ok=True)

# =========================
# COLOR SCHEME
# =========================
CAT_COLORS = {
    'Languages': '#1B3A6B',
    'Cloud': '#2E6DA4',
    'ETL Tools': '#E8A020',
    'Orchestration': '#27AE60',
    'Processing': '#8E44AD',
    'Data Warehouses': '#E74C3C',
    'DevOps': '#16A085',
    'Modern/AI': '#D35400',
    'BI/Viz': '#7F8C8D',
}

CATEGORIES = {
    'Languages': ['Python', 'SQL', 'Scala', 'Java', 'Bash/Shell'],
    'Cloud': ['AWS', 'Azure', 'GCP'],
    'ETL Tools': ['AWS Glue', 'Azure Data Factory', 'GCP Dataflow', 'dbt', 'Informatica', 'Talend', 'Fivetran', 'Airbyte'],
    'Orchestration': ['Apache Airflow', 'Prefect', 'Dagster'],
    'Processing': ['Apache Spark', 'Apache Kafka', 'Apache Flink', 'Apache Hadoop', 'Databricks'],
    'Data Warehouses': ['Snowflake', 'Redshift', 'BigQuery', 'PostgreSQL'],
    'DevOps': ['Docker', 'Kubernetes', 'Terraform', 'CI/CD'],
    'Modern/AI': ['Serverless', 'Machine Learning'],
    'BI/Viz': ['Tableau', 'Power BI', 'Looker'],
}

def get_category(tech):
    for cat, techs in CATEGORIES.items():
        if tech in techs:
            return cat
    return 'Other'

# =========================
# FREQUENCY TABLE
# =========================
all_tech_counts = Counter()
for tech_set in df_de['technologies']:
    all_tech_counts.update(tech_set)

freq_df = pd.DataFrame(all_tech_counts.items(), columns=['Technology', 'Count'])
freq_df['Percentage'] = (freq_df['Count'] / len(df_de) * 100).round(1)
freq_df['Category'] = freq_df['Technology'].apply(get_category)
freq_df = freq_df.sort_values(['Count', 'Technology'], ascending=[False, True]).reset_index(drop=True)  # deterministic tie-break

print("=" * 55)
print(f"GLOBAL TECHNOLOGY ADOPTION RATES (n={len(df_de)} postings)")
print("=" * 55)
print(f"{'Rank':<5} {'Technology':<25} {'Count':>5}  {'Pct':>6}")
print("-" * 55)
for i, row in freq_df.iterrows():
    print(f"{i+1:<5} {row['Technology']:<25} {row['Count']:>5}  {row['Percentage']:>5.1f}%")

freq_df.to_csv('outputs/table_tech_frequency.csv', index=False)

# =========================
# FIGURE 1 — TOP 25 TECHNOLOGIES
# =========================
top25 = freq_df.head(25).copy()
bar_colors = [CAT_COLORS.get(cat, '#999') for cat in top25['Category']]

fig, ax = plt.subplots(figsize=(14, 8))
bars = ax.barh(range(len(top25)), top25['Percentage'], color=bar_colors, edgecolor='white', height=0.7)

for bar, pct in zip(bars, top25['Percentage']):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2, f'{pct:.1f}%', va='center', fontsize=8.5, color='#6B7C93')

ax.set_yticks(range(len(top25)))
ax.set_yticklabels(top25['Technology'], fontsize=10)
ax.invert_yaxis()
ax.set_xlabel('% of Data Engineering Job Postings', fontsize=11)
ax.set_title(
    f'Figure 1. Top 25 Technologies in Global Data Engineering Job Postings\n(n = {len(df_de)} postings, public job-posting dataset, 2025)',
    fontsize=13, fontweight='bold', pad=15
)
ax.axvline(50, color='gray', linestyle='--', alpha=0.3, linewidth=1)
ax.set_xlim(0, max(top25['Percentage']) * 1.15)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

legend_patches = [mpatches.Patch(color=v, label=k) for k, v in CAT_COLORS.items()]
ax.legend(handles=legend_patches, loc='lower right', fontsize=8.5, title='Category', title_fontsize=9, framealpha=0.9)

plt.tight_layout()
plt.savefig('outputs/fig1_tech_frequency.png', bbox_inches='tight', dpi=150)
plt.close()
print("\nFigure 1 saved to outputs/fig1_tech_frequency.png")

# =========================
# FIGURE 2 — CATEGORY AVERAGE
# =========================
cat_order = ['Languages', 'Cloud', 'ETL Tools', 'Orchestration', 'Processing', 'Data Warehouses', 'DevOps', 'Modern/AI', 'BI/Viz']
cat_avg = freq_df.groupby('Category')['Percentage'].mean().reindex(cat_order).dropna()

fig, ax = plt.subplots(figsize=(11, 5))
bars = ax.bar(range(len(cat_avg)), cat_avg.values, color=[CAT_COLORS[c] for c in cat_avg.index], edgecolor='white', width=0.6)

for bar, val in zip(bars, cat_avg.values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f'{val:.1f}%', ha='center', fontsize=9.5, fontweight='bold')

ax.set_xticks(range(len(cat_avg)))
ax.set_xticklabels(cat_avg.index, rotation=25, ha='right', fontsize=10)
ax.set_ylabel('Average Mention Rate (%)', fontsize=11)
ax.set_title(
    'Figure 2. Average Technology Mention Rate by Category\nGlobal Data Engineering Roles (public job-posting dataset, 2025)',
    fontsize=12, fontweight='bold', pad=12
)
ax.set_ylim(0, max(cat_avg.values) * 1.2)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('outputs/fig2_category_avg.png', bbox_inches='tight', dpi=150)
plt.close()
print("Figure 2 saved to outputs/fig2_category_avg.png")

# =========================
# QUALIFY TECHNOLOGIES FOR ASSOCIATION ANALYSIS
# =========================
min_count = int(len(df_de) * 0.05)
qualified_techs = [t for t, c in all_tech_counts.items() if c >= min_count]

print(f"Technologies meeting 5% threshold: {len(qualified_techs)}")
print(f"Qualified: {sorted(qualified_techs)}")

transactions = [list(tech_set & set(qualified_techs)) for tech_set in df_de['technologies']]
transactions = [t for t in transactions if t]

te = TransactionEncoder()
te_array = te.fit_transform(transactions)
df_bin = pd.DataFrame(te_array, columns=te.columns_)

print(f"\nBinary matrix shape: {df_bin.shape}")
print("(rows = postings, columns = technologies)")

# =========================
# CO-OCCURRENCE MATRIX
# =========================
co_matrix = pd.DataFrame(0, index=qualified_techs, columns=qualified_techs)

for tech_set in df_de['technologies']:
    t_list = list(tech_set & set(qualified_techs))
    for i in range(len(t_list)):
        for j in range(len(t_list)):
            if i != j:
                co_matrix.loc[t_list[i], t_list[j]] += 1

co_norm = co_matrix.div(co_matrix.max(axis=1).replace(0, 1), axis=0)

# =========================
# FIGURE 3 — CO-OCCURRENCE HEATMAP
# =========================
top18 = freq_df[freq_df['Technology'].isin(qualified_techs)].head(18)['Technology'].tolist()
co_sub = co_norm.loc[top18, top18]

fig, ax = plt.subplots(figsize=(13, 11))
mask = np.eye(len(top18), dtype=bool)

sns.heatmap(
    co_sub, ax=ax, mask=mask,
    cmap='Blues', linewidths=0.4, linecolor='white',
    annot=False,
    cbar_kws={'label': 'Normalized Co-occurrence', 'shrink': 0.8}
)

ax.set_title(
    'Figure 3. Technology Co-occurrence Heat Map\nTop 18 Data Engineering Technologies (Normalized)',
    fontsize=13, fontweight='bold', pad=15
)
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=9)
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)

plt.tight_layout()
plt.savefig('outputs/fig3_cooccurrence_heatmap.png', bbox_inches='tight', dpi=150)
plt.close()
print("\nFigure 3 saved to outputs/fig3_cooccurrence_heatmap.png")

# =========================
# ASSOCIATION RULE MINING
# =========================
min_support = min_count / len(df_bin) if len(df_bin) > 0 else 0.05
frequent_sets = apriori(df_bin, min_support=min_support, use_colnames=True)

rules = association_rules(
    frequent_sets,
    metric='lift',
    min_threshold=1.2,
    num_itemsets=len(frequent_sets)
)
rules = rules.sort_values('lift', ascending=False).reset_index(drop=True)

print("\n" + "=" * 75)
print("TOP 15 ASSOCIATION RULES (sorted by Lift)")
print("=" * 75)
print(f"{'Antecedent':<22} {'Consequent':<22} {'Support':>8} {'Confidence':>11} {'Lift':>7}")
print("-" * 75)

for _, r in rules.head(15).iterrows():
    ant = ', '.join(list(r['antecedents']))
    con = ', '.join(list(r['consequents']))
    print(f"{ant:<22} {con:<22} {r['support']:>7.1%} {r['confidence']:>10.1%} {r['lift']:>7.2f}")

# =========================
# FIGURE 4 — ASSOCIATION RULES
# =========================
top_rules = rules.head(20).copy()

fig, ax = plt.subplots(figsize=(12, 8))
scatter = ax.scatter(
    top_rules['support'],
    top_rules['confidence'],
    s=top_rules['lift'] * 120,
    alpha=0.7,
    c=top_rules['lift'],
    cmap='Blues',
    edgecolors='#1B3A6B',
    linewidth=0.8
)

for _, r in top_rules.head(10).iterrows():
    ant = ', '.join(list(r['antecedents']))
    con = ', '.join(list(r['consequents']))
    label = f"{ant} → {con}"
    if len(label) > 40:
        label = label[:38] + '…'
    ax.annotate(
        label,
        (r['support'], r['confidence']),
        textcoords='offset points',
        xytext=(6, 4),
        fontsize=7.5,
        color='#1B3A6B',
        alpha=0.85
    )

cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Lift', fontsize=10)
ax.set_xlabel('Support (% of postings containing both technologies)', fontsize=11)
ax.set_ylabel('Confidence', fontsize=11)
ax.set_title(
    'Figure 4. Association Rules — Technology Co-adoption Patterns\n(Bubble size = Lift; higher lift = stronger association)',
    fontsize=12, fontweight='bold', pad=12
)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('outputs/fig4_association_rules.png', bbox_inches='tight', dpi=150)
plt.close()
print("Figure 4 saved to outputs/fig4_association_rules.png")

# =========================
# GAP ANALYSIS
# =========================
COMPANY_X_STACK = {
    'Python': True,
    'SQL': True,
    'Scala': False,
    'Java': False,
    'AWS': False,
    'Azure': False,
    'GCP': False,
    'AWS Glue': False,
    'Azure Data Factory': False,
    'GCP Dataflow': False,
    'dbt': False,
    'Informatica': False,
    'Talend': False,
    'Apache Airflow': False,
    'Apache Spark': False,
    'Apache Kafka': False,
    'Apache Hadoop': False,
    'Databricks': False,
    'Snowflake': False,
    'Redshift': False,
    'BigQuery': False,
    'PostgreSQL': False,
    'Docker': False,
    'Kubernetes': False,
    'Terraform': False,
    'CI/CD': False,
    'Serverless': False,
    'Machine Learning': False,
    'Tableau': True,
    'Power BI': True,
    'Looker': False,
}

def classify_status(tech, in_use, global_pct):
    if in_use:
        return 'In Use'
    elif global_pct >= 20.0:
        return 'Gap'
    else:
        return 'Low Priority'

comparison_rows = []
for _, row in freq_df.iterrows():
    tech = row['Technology']
    if tech not in COMPANY_X_STACK:
        continue
    in_use = COMPANY_X_STACK[tech]
    status = classify_status(tech, in_use, row['Percentage'])
    comparison_rows.append({
        'Technology': tech,
        'Category': row['Category'],
        'Global Rank': row.name + 1,
        'Global Adoption (%)': row['Percentage'],
        'Company X': 'In Use' if in_use else 'Not in Use',
        'Status': status,
    })

comp_df = pd.DataFrame(comparison_rows).sort_values('Global Adoption (%)', ascending=False).reset_index(drop=True)

gaps = comp_df[comp_df['Status'] == 'Gap']
in_use = comp_df[comp_df['Status'] == 'In Use']
low_prio = comp_df[comp_df['Status'] == 'Low Priority']

print("=" * 65)
print("GAP ANALYSIS — Company X vs. Global Benchmark")
print("=" * 65)
print(f"{'Technology':<25} {'Global %':>9}  {'Company X':<12}  Status")
print("-" * 65)
for _, r in comp_df.iterrows():
    print(f"{r['Technology']:<25} {r['Global Adoption (%)']:>8.1f}%  {r['Company X']:<12}  {r['Status']}")

print("\n" + "=" * 40)
print("SUMMARY")

# =========================
# FIGURE 1 (paper style) - top technologies incl. ties at the cut-off
# =========================
# Same look as the figure embedded in the paper; shows 26 bars because
# Docker and Azure Data Factory tie for 25th place (20 postings each).
fig, ax = plt.subplots(figsize=(7.19, 5.19), dpi=300)
top = freq_df.head(26)
ax.barh(range(len(top)), top['Percentage'], color='#1f77b4', height=0.8)
ax.set_yticks(range(len(top)))
ax.set_yticklabels(top['Technology'], fontsize=10)
ax.invert_yaxis()
ax.set_xlabel('% of data engineering postings', fontsize=10)
ax.set_title(f'Top 26 Technologies in Global Data Engineering Job Postings (n = {len(df_de)})', fontsize=11.5)
ax.grid(axis='x', alpha=0.25)
ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig('outputs/fig1_paper_style.png', dpi=300)
plt.close()
print("Paper-style Figure 1 saved to outputs/fig1_paper_style.png")

print("=" * 40)
print(f"  Technologies in use            : {len(in_use)}")
print(f"  Critical gaps (>=20% globally) : {len(gaps)}")
print(f"  Low priority (<20% globally)   : {len(low_prio)}")
print("\nCritical gaps:")
for _, r in gaps.iterrows():
    print(f"  - {r['Technology']:<25} {r['Global Adoption (%)']:.1f}% global adoption")

comp_df.to_csv('outputs/table_gap_analysis.csv', index=False)
print("\nTables saved to outputs/")

# =========================
# FIGURE 5 — GAP ANALYSIS BAR CHART
# =========================
STATUS_COLORS = {
    'In Use': '#27AE60',
    'Gap': '#E74C3C',
    'Low Priority': '#F39C12',
}

top_comp = comp_df.head(20).copy()
x = np.arange(len(top_comp))
bar_colors = [STATUS_COLORS[s] for s in top_comp['Status']]

fig, ax = plt.subplots(figsize=(14, 7))
bars = ax.bar(x, top_comp['Global Adoption (%)'], color=bar_colors, edgecolor='white', width=0.65)

for bar, row in zip(bars, top_comp.itertuples(index=False)):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() / 2,
        f"{row._3:.0f}%",
        ha='center', va='center',
        fontsize=8.5, color='white', fontweight='bold'
    )

ax.set_xticks(x)
ax.set_xticklabels(top_comp['Technology'], rotation=40, ha='right', fontsize=9.5)
ax.set_ylabel('Global Adoption Rate (%)', fontsize=11)
ax.set_title(
    'Figure 5. Company X Technology Stack vs. Global Industry Benchmark\n(Green = In Use  |  Red = Critical Gap  |  Orange = Low Priority)',
    fontsize=12, fontweight='bold', pad=12
)
legend_patches = [mpatches.Patch(color=v, label=k) for k, v in STATUS_COLORS.items()]
ax.legend(handles=legend_patches, fontsize=9.5, loc='upper right')
ax.set_ylim(0, max(top_comp['Global Adoption (%)']) * 1.2)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('outputs/fig5_gap_analysis.png', bbox_inches='tight', dpi=150)
plt.close()
print("Figure 5 saved to outputs/fig5_gap_analysis.png")

# =========================
# FIGURE 6 — CLOUD / ETL ADOPTION
# =========================
cloud_techs = ['AWS', 'Azure', 'GCP', 'AWS Glue', 'Azure Data Factory', 'GCP Dataflow', 'Snowflake', 'Databricks', 'BigQuery', 'Redshift']
cloud_df = freq_df[freq_df['Technology'].isin(cloud_techs)].sort_values('Percentage', ascending=True).copy()

fig, ax = plt.subplots(figsize=(10, 6))
c_colors = [CAT_COLORS.get(r['Category'], '#999') for _, r in cloud_df.iterrows()]
bars = ax.barh(cloud_df['Technology'], cloud_df['Percentage'], color=c_colors, edgecolor='white', height=0.6)

for bar, pct in zip(bars, cloud_df['Percentage']):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2, f'{pct:.1f}%', va='center', fontsize=9.5)

ax.set_xlabel('% of Data Engineering Job Postings', fontsize=11)
ax.set_title(
    'Figure 6. Cloud Platform & Managed ETL Tool Adoption\nGlobal Data Engineering Roles (public job-posting dataset, 2025)',
    fontsize=12, fontweight='bold', pad=12
)
ax.set_xlim(0, max(cloud_df['Percentage']) * 1.25 if len(cloud_df) else 1)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

legend_patches = [
    mpatches.Patch(color=CAT_COLORS['Cloud'], label='Cloud Platform'),
    mpatches.Patch(color=CAT_COLORS['ETL Tools'], label='Managed ETL Tool'),
    mpatches.Patch(color=CAT_COLORS['Data Warehouses'], label='Cloud Data Warehouse'),
]
ax.legend(handles=legend_patches, fontsize=9)

plt.tight_layout()
plt.savefig('outputs/fig6_cloud_adoption.png', bbox_inches='tight', dpi=150)
plt.close()
print("Figure 6 saved to outputs/fig6_cloud_adoption.png")

print("\n" + "=" * 40)
print("WEEK 1 ANALYSIS COMPLETE")
print("All figures saved to outputs/")
print("=" * 40)