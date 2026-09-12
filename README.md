# BankSight: Synthetic Banking Data Analysis

An end-to-end data analysis project on a synthetic banking dataset (50K customers,
75K accounts, 100K cards, 30K loans, 1M transactions, 2019–2025), combining **SQL**
(SQLite) with **Python** (pandas, matplotlib, seaborn) for analysis, plus a Power BI
dashboard (in progress).

## Getting the data

This repo doesn't include the dataset (raw data ~650MB, over GitHub's size limits).
Search Kaggle for "synthetic banking dataset" or use your own copy of
`archive__1_.zip`, and place its contents at `data/raw/banking_dataset_kaggle/`.
Running the scripts in `src/` will regenerate everything in `data/cleaned/`.

## What's inside

- `data/raw/` — original dataset: CSVs, SQLite DB, SQL schema *(not tracked in git — see "Getting the data" above)*
- `data/cleaned/` — exported/derived tables: customer segments, flagged transactions *(not tracked in git — regenerate via the scripts below)*
- `notebooks/banking_analysis.ipynb` — full narrated analysis notebook
- `src/` — Python scripts for data quality checks, SQL queries, visualization, segmentation, and anomaly detection
- `figures/` — chart images
- `reports/FINDINGS_PLAIN_LANGUAGE.md` — plain-language summary of findings

## Key Findings

1. Data is fully clean — zero nulls, duplicates, or broken foreign keys
2. Account type (Checking/Savings/Business) doesn't meaningfully differentiate balance
3. **Credit score has no relationship with loan interest rate** — the most important finding
4. Credit scores and transaction amounts are uniformly (not realistically) distributed — a synthetic-data signature
5. Customer segmentation and anomaly-flagging methods are sound, but thresholds would need recalibrating against real-world data

Full details: see `reports/FINDINGS_PLAIN_LANGUAGE.md` or the notebook.

## Tools

Python (pandas, sqlite3, matplotlib, seaborn), SQL (SQLite), Jupyter, Power BI (in progress)

## Reproducing this analysis

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install pandas numpy matplotlib seaborn jupyter nbconvert nbformat ipykernel
python src\01_data_quality.py
python src\02_sql_queries.py
python src\03_visualize.py
python src\04_segmentation.py
python src\05_anomaly_detection.py
```