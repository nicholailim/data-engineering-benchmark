# Code and supporting materials for:

**“Benchmarking Data Engineering Technology Adoption and Cloud Migration Feasibility: A Data-Driven Case Study”**

5th International Conference on Innovations in Data Analytics (ICIDA 2026), Paper ID 712 (Springer LNNS).

**Authors:** Nicholai Matthew E. Lim and John Paul Q. Tomas  
**Affiliation:** Mapúa University, Makati, Philippines

## 1. Repository contents

| Path | Purpose |
|---|---|
| `scripts/01_extract_and_benchmark.py` | Filters the job-posting data, identifies technology mentions, and generates technology-frequency, co-occurrence, association-rule, and gap-analysis outputs. |
| `scripts/02_cloud_cost_model.py` | Calculates monthly costs, total cost of ownership, ROI, and weighted scores for AWS Glue, Azure Data Factory, and Google Cloud Dataflow against the on-premises baseline. |
| `scripts/03_mcda_weight_sensitivity.py` | Tests alternative decision-weight sets, score changes, and random weight distributions. |
| `scripts/04_cost_sensitivity.py` | Tests cost-model assumptions including lost productivity, ADF vCores, Glue Flex pricing, job duration, exchange rate, and migration cost. |
| `scripts/05_carbon_estimates.py` | Calculates the emissions scenarios and bottom-up estimate reported in the paper. |
| `scripts/06_extraction_validation_sample.py` | Reconstructs the 30-posting sample used for the manual extraction check and prints matching text from the locally supplied dataset. |
| `data/README.md` | Documents the required input dataset, its schema, provenance, and preparation limitations. |
| `validation/` | Contains the recorded manual validation judgments. Source-description context excerpts are not redistributed. |
| `expected_outputs/` | Contains selected expected tables, figures, and console outputs for comparison. |

## 2. Requirements

The scripts were developed and tested with Python 3.12 and the package versions listed in the project environment:

- pandas 3.0
- NumPy 2.4
- Matplotlib 3.10
- seaborn 0.13
- mlxtend 0.25

Install the dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

The `requirements.txt` file specifies minimum package versions. For strict environment replication, record the exact versions installed in your environment (for example, with `python -m pip freeze`) and retain that environment record with your research materials.

## 3. Input data

The dataset file `data/clean_jobs.csv` is **not included** in this repository. It must be obtained separately from the source described in [`data/README.md`](data/README.md), subject to that source's licence and terms.

Place the prepared file at:

```text
data/clean_jobs.csv
```

The expected schema is:

```text
id, title, company, location, link, source, date_posted,
work_type, employment_type, description
```

The analysis scripts do not download the source data or create `clean_jobs.csv` from the original Kaggle download. They expect the prepared 1,048-row CSV as input. The repository therefore documents the input and the analysis-stage filtering, but does not claim that the original-download-to-CSV preparation is fully automated here.

## 4. Run the analyses

Run commands from the repository root.

### Dataset-dependent scripts

After placing `clean_jobs.csv` in `data/`, run:

```bash
python scripts/01_extract_and_benchmark.py
python scripts/06_extraction_validation_sample.py
```

Script 01 applies the data-engineering role-title filter, removes exact duplicate descriptions, and excludes records with missing descriptions. The reported dataset flow is 1,048 source records, 219 records after the role-title filter, and 186 unique postings after deduplication and missing-description exclusion.

Script 06 uses the same filtering and sampling procedure to reconstruct the 30-posting validation sample. It reads the local dataset to display matching text; the repository's validation CSV contains the recorded judgments without redistributing the original context excerpts.

### Dataset-independent scripts

These scripts do not require `clean_jobs.csv`:

```bash
python scripts/02_cloud_cost_model.py
python scripts/03_mcda_weight_sensitivity.py
python scripts/04_cost_sensitivity.py
python scripts/05_carbon_estimates.py
```

Generated files are written to `outputs/`. The `outputs/` directory is intentionally excluded from version control; selected reference outputs are preserved in `expected_outputs/`.

## 5. Validation and interpretation

The validation records in `validation/extraction_validation_30_postings.csv` document the manual judgments for the sampled postings. The judgments relate to the initial extraction patterns; Script 01 contains the revised patterns. Script 06 displays matches produced by the current patterns, so its displayed matches should not be interpreted as a verbatim reproduction of the original manual-review context.

The cost, migration, productivity, and decision-score inputs include author-defined assumptions. The carbon estimate of 346 kWh/year is a conservative planning scenario, not a direct measurement; the bottom-up estimate is a separate model-based cross-check. Consult the paper for the assumptions, definitions, limitations, and interpretation of each result.

Provider prices and the PHP 59.00/USD exchange-rate assumption are dated in the paper. They may change over time, so rerunning the model with current prices may not reproduce the published values.

## 6. Expected outputs

Use the files in `expected_outputs/` as reference outputs when checking a run. Small differences may occur because of changes in package versions, floating-point calculations, or source data revisions. Investigate material differences rather than assuming they are harmless.

## 7. Data use and licensing

The code is released under the MIT License; see [`LICENSE`](LICENSE). This licence applies to the code in this repository, not to the separately sourced Kaggle dataset or third-party job-posting content.

The source dataset is not redistributed here. Users are responsible for obtaining it lawfully and complying with the dataset's current licence and terms. Do not redistribute the source dataset or copied job-description text unless the applicable terms permit it.

## 8. Citation

Please cite the research paper when using this code. Machine-readable citation metadata are provided in [`CITATION.cff`](CITATION.cff). After the repository has been archived in Zenodo, add the version-specific DOI to the citation metadata and README.