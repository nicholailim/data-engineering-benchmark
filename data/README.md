# Input data: `clean_jobs.csv`

## 1. Availability and source

The file `clean_jobs.csv` is required by:

- `scripts/01_extract_and_benchmark.py`
- `scripts/06_extraction_validation_sample.py`

It is **not included** in this repository.

The source identified for the study is:

- **Dataset:** *LinkedIn Data Jobs Dataset*
- **Provider/author shown on Kaggle:** J. Kimaiyo (2025)
- **Source page:** https://www.kaggle.com/datasets/joykimaiyo18/linkedin-data-jobs-dataset

The Kaggle dataset page indicates non-commercial-use conditions. Check the current dataset licence and terms directly before downloading, using, or redistributing the data. The MIT licence in this code repository does not grant rights to the Kaggle data or to the job advertisements.

## 2. Required prepared input

The analysis scripts expect a prepared CSV named exactly:

```text
clean_jobs.csv
```

The version used for the reported analysis is described as containing **1,048 rows** and the following columns, in this order:

```text
id
title
company
location
link
source
date_posted
work_type
employment_type
description
```

The postings used in the study were published between **10 April and 11 June 2025**. The reported source distribution after the analysis-stage filtering is 172 records labelled `LinkedIn` and 14 labelled `Indeed` in the `source` column.

## 3. What the analysis scripts do

Starting with the prepared 1,048-row `clean_jobs.csv`, Script 01:

1. Reads the CSV from `data/clean_jobs.csv`.
2. Retains records whose `title` contains one or more of the data-engineering role keywords defined in the script. The reported count after this role-title filter is 219.
3. Removes exact duplicate values in the `description` column.
4. Excludes records with missing `description` values.
5. Uses the resulting 186 postings for technology extraction and subsequent analysis.

Script 06 repeats the role-title filter, exact-description deduplication, and missing-description exclusion so it can reconstruct the 186-posting analysis population and the 30-posting sample.

These are the analysis-stage operations implemented in the repository. They should not be confused with any preparation that may have been performed on the original Kaggle download before the 1,048-row `clean_jobs.csv` was created.

## 4. Recreating the prepared CSV

**Reproducibility note:** The original-download-to-`clean_jobs.csv` transformation is not implemented as a separate script in this repository, and the precise sequence of source-file selection, merging, column mapping, and preliminary cleaning is not recorded in the supplied code package.

Accordingly, this repository does not claim that the 1,048-row prepared input can be reconstructed from the Kaggle download using the included scripts alone. To reproduce the input exactly, the researchers should document and retain the actual preparation procedure used to create their copy of `clean_jobs.csv`, including:

- The exact Kaggle file name(s) downloaded and the download/access date.
- Whether one file was used or multiple files were combined.
- Any column renaming, selection, or reordering.
- Any row filtering or removal of incomplete records performed before the 1,048-row file was saved.
- Any type conversion, date parsing, text normalization, or deduplication performed before the analysis scripts were run.
- Confirmation that the final file has 1,048 rows and the ten columns listed above.

Do not infer or add preparation steps that were not actually performed. If the original preparation process cannot be recovered, state that limitation rather than presenting an assumed procedure as fact.

## 5. Data integrity checks before running

Before running Scripts 01 and 06, check that:

- The file is named `clean_jobs.csv`.
- It is saved in this `data/` directory.
- It is comma-delimited and can be read as UTF-8 CSV.
- All ten required columns are present.
- The file has 1,048 data rows, excluding the header.
- `title` and `description` contain the values used in the study.

The scripts expect the column names shown above. If your downloaded data has a different schema, prepare a separate working copy with the required names and structure; do not overwrite the original downloaded file.

## 6. Data redistribution

The dataset is intentionally omitted from this repository. Obtain it directly from its source and follow its current licence and terms. Do not upload `clean_jobs.csv`, the original downloaded files, or copied job-description text to GitHub or Zenodo unless you have confirmed that redistribution is permitted.