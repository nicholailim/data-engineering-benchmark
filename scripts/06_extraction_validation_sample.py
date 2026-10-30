"""
06_extraction_validation_sample.py
Re-draws the random sample of 30 postings used for the manual check of the technology
extraction (Section 3.1) and prints, for each posting, the technologies flagged by the
extraction patterns together with the surrounding text.

Sampling: filtered dataset of 186 postings, random.seed(42), random.sample(range(186), 30),
indices sorted.  The manual judgements in validation/extraction_validation_30_postings.csv
were made on the INITIAL patterns (before the alias fixes); the output of this script uses
the revised patterns in 01_extract_and_benchmark.py.

Run from the repository root:
    python scripts/06_extraction_validation_sample.py
"""
import random, re, ast
import pandas as pd

DE_KEYWORDS = ['data engineer', 'etl', 'data pipeline', 'analytics engineer', 'data integration',
               'data platform', 'data infrastructure', 'pipeline engineer']

df = pd.read_csv('data/clean_jobs.csv')
df = df[df['title'].apply(lambda t: any(k in str(t).lower() for k in DE_KEYWORDS))].copy()
df = df.drop_duplicates(subset=['description']).dropna(subset=['description'])
df['description'] = df['description'].astype(str)
assert len(df) == 186, len(df)

# read the TECH_DICT literal from script 01 (no plotting is triggered)
src = open('scripts/01_extract_and_benchmark.py', encoding='utf-8').read()
start = src.index('TECH_DICT = {')
end = src.index('\n}', start) + 2
TECH_DICT = ast.literal_eval(src[start + len('TECH_DICT = '):end].replace('\r', ''))

random.seed(42)
idx = sorted(random.sample(range(len(df)), 30))
sample = df.iloc[idx].reset_index(drop=True)

check = pd.read_csv('validation/extraction_validation_30_postings.csv')
expected = check.drop_duplicates('sample_no').sort_values('sample_no')['title'].tolist()
assert sample['title'].tolist() == expected, 'sample differs from the one that was manually checked'
print('Sample matches the 30 postings in validation/extraction_validation_30_postings.csv\n')

for i, row in sample.iterrows():
    text = row['description'].lower()
    print(f"#{i + 1} {row['title']}")
    for tech, patterns in TECH_DICT.items():
        for p in patterns:
            m = re.search(p, text)
            if m:
                ctx = text[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')
                print(f'   {tech:20s} ...{ctx}...')
                break
