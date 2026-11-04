# Automated Data Cleaning & Schema Transformation

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/pytest-31%20passed-brightgreen.svg)](tests/)
[![Code Style](https://img.shields.io/badge/Code%20Style-PEP%208-informational.svg)](https://pep8.org/)
[![Internship](https://img.shields.io/badge/Internship-Datheon-orange.svg)]()

> A production-style, configurable Python data engineering pipeline designed to ingest messy, unstandardized CSV files and transform them into clean, type-safe, validated datasets accompanied by automated audit logs and executive quality reports.

---

## 1. Project Overview

In data engineering pipelines, raw incoming datasets from transactional databases, web forms, and legacy third-party feeds are notoriously inconsistent. They frequently arrive with mixed date patterns, localized currency symbols, missing attributes, unstandardized headers, duplicated rows, and out-of-bounds anomaly values.

This project delivers a **modular, rule-driven ETL application** that automates the data cleansing and schema transformation lifecycle. Instead of hardcoding transformations for a single file, the pipeline executes against a decoupled **JSON configuration schema**, enabling data teams to reuse the same framework across diverse datasets with zero code alterations.

---

## 2. Problem Statement

Data engineers spend up to 80% of their operational bandwidth writing repetitive ad-hoc scripts to fix dirty data:
- **Corrupt & Mixed Dates**: Disparate conventions (`DD-MM-YYYY`, `YYYY/MM/DD`, `DD Mon YYYY`) crash analytical warehouses.
- **Heterogeneous Currencies**: Mixed strings (`₹25,000`, `INR 25000`, `Rs. 25,000`, `$500`) prevent mathematical aggregations.
- **Silent Data Loss**: Blindly dropping or replacing missing values introduces statistical bias and corrupts downstream models.
- **Duplicate Records**: Multiple submissions or primary key collisions distort business reporting.
- **Schema Drift**: Uncoordinated column additions, inconsistent casing, and whitespace-padded headers break downstream SQL tables.

---

## 3. Project Objectives

1. **Automate Ingestion & Profiling**: Safely ingest CSV files across various encodings (`utf-8`, `latin1`, `cp1252`) and extract initial statistics before mutating data.
2. **Deterministic Data Normalization**: Strip currency symbols, parse international formats into `float64`, and standardize ambiguous dates into ISO `YYYY-MM-DD`.
3. **Transparent Imputation**: Apply configurable mean, median, mode, or custom strategies while purging non-informative columns (>90% missing).
4. **Data Quarantine Protocol**: Prevent corrupted records from entering production by isolating invalid rows into a quarantine dataset (`invalid_records.csv`) alongside actionable rejection reasons.
5. **Full Auditability**: Produce machine-readable JSON metrics and a styled HTML executive dashboard summarizing transformations and rule violations.

---

## 4. Key Features

- **Multi-Encoding CSV Loader**: Automatically falls back across encodings and validates file boundaries (detects 0-byte files, structural corruption).
- **Automated Data Profiler**: Pre-cleaning diagnostic report identifying null percentages, unique cardinalities, exact duplicate rows, and numerical outliers using the Interquartile Range (IQR = $Q_3 - Q_1$).
- **Configurable Imputation Engine**: Strategy-driven missing-value handler supporting numerical mean/median, categorical mode, and custom fill values.
- **Deduplication Engine**: Full-row deduplication and subset-based primary key deduplication preserving the first valid occurrence.
- **Robust Currency Normalizer**: Vectorized regex engine supporting Indian Rupee (`₹`, `INR`, `Rs.`), US Dollar (`$`), Euro (`€`), accounting parentheses `(1,500)`, and negative numbers.
- **Ambiguous Date Engine**: Multi-format parser with configurable `day_first` disambiguation to prevent silent date corruption.
- **Schema Transformer**: Converts headers into uniform `snake_case`, applies column alias mappings, enforces nullable Pandas dtypes (`Int64`, `float64`, `string`, `boolean`), and locks column sequencing.
- **Quarantine Validation Engine**: Evaluates primary key uniqueness, mandatory field presence, acceptable numerical intervals (e.g., $18 \le \text{age} \le 100$), and regex patterns (email syntax).
- **Dual Reporting**: Exports comprehensive `validation_report.json` and a modern, responsive `cleaning_summary.html`.
- **Rotating File Logging**: Uses `RotatingFileHandler` (5MB rollover, 3 backups) to eliminate disk bloat in continuous execution environments.

---

## 5. Technology Stack

| Technology | Purpose |
| :--- | :--- |
| **Python 3.11 - 3.13** | Core language runtime |
| **Pandas (>=2.2.0)** | High-performance vectorized DataFrame manipulation and nullable types |
| **NumPy (>=1.26.0)** | Array operations, IQR quantile calculations, NaN representations |
| **pytest (>=8.0.0)** | Automated unit, negative, and integration test suite |
| **Argparse** | Command-Line Interface (CLI) parsing |
| **Logging & RotatingFileHandler** | Production logging with log rotation |
| **Pathlib** | Cross-platform filesystem navigation (Windows/Linux/macOS) |
| **JSON & Re** | Schema configuration parsing and regular expressions |

---

## 6. Architecture & Pipeline Workflow

```
+-----------------------------------------------------------------------+
|                         RAW INPUT CSV FILE                            |
+-----------------------------------------------------------------------+
                                   |
                                   v
                      +--------------------------+
                      |   Module 1: DataLoader   |  (Multi-encoding, empty check)
                      +--------------------------+
                                   |
                                   v
                      +--------------------------+
                      |  Module 2: DataProfiler  |  (Nulls, Outliers via IQR)
                      +--------------------------+
                                   |
                                   v
                      +--------------------------+
                      | Module 7: Header Normal  |  (Trimming, snake_case, Aliases)
                      +--------------------------+
                                   |
                                   v
                      +--------------------------+
                      | Module 5: Currency Clean |  (Symbols, negatives, floats)
                      +--------------------------+
                                   |
                                   v
                      +--------------------------+
                      |  Module 6: Date Normal   |  (Day-first, ISO YYYY-MM-DD)
                      +--------------------------+
                                   |
                                   v
                      +--------------------------+
                      | Module 3: Missing Impute |  (Mean/Median/Mode, Drop empty)
                      +--------------------------+
                                   |
                                   v
                      +--------------------------+
                      | Module 4: Deduplication  |  (Full row & PK subset)
                      +--------------------------+
                                   |
                                   v
                      +--------------------------+
                      | Module 7: Schema Casting |  (Int64, float64, boolean, order)
                      +--------------------------+
                                   |
                                   v
                      +--------------------------+
                      |  Module 8: DataValidator |
                      +--------------------------+
                                   |
                 +-----------------+-----------------+
                 |                                   |
                 v                                   v
       [Passed Validation]                 [Violations Quarantined]
                 |                                   |
                 v                                   v
        cleaned_data.csv                    invalid_records.csv
                 |                                   |
                 +-----------------+-----------------+
                                   |
                                   v
               +----------------------------------------+
               |  Modules 9-11: Reporting & Log Export  |
               +----------------------------------------+
                 |                 |                  |
                 v                 v                  v
       validation_report.json  summary.html      cleaning.log
```

---

## 7. Folder Structure

```
automated-data-cleaning/
│
├── data/
│   ├── raw/
│   │   └── sample_messy_data.csv       # 120-row synthetic dataset with real-world flaws
│   └── output/                         # Target directory for generated artifacts
│       ├── .gitkeep
│       ├── cleaned_data.csv            # Clean, production-ready dataset
│       ├── invalid_records.csv         # Quarantined rows with explicit rejection reasons
│       ├── validation_report.json      # Machine-readable execution & audit report
│       ├── cleaning_summary.html       # Visual executive HTML dashboard
│       └── cleaning.log                # Rotating execution log file
│
├── config/
│   └── schema_config.json              # Decoupled schema, rules, and imputation specs
│
├── src/
│   ├── __init__.py                     # Package initialization
│   ├── loader.py                       # Module 1: Resilient CSV file ingestion
│   ├── profiler.py                     # Module 2: Data inspection & IQR outlier detection
│   ├── missing_values.py               # Module 3: Missing value imputation & pruning
│   ├── duplicates.py                   # Module 4: Deduplication logic
│   ├── currency.py                     # Module 5: Currency parsing & symbol stripping
│   ├── dates.py                        # Module 6: Polymorphic date standardization
│   ├── schema_transformer.py           # Module 7: Snake_casing, aliases, and type casting
│   ├── validator.py                    # Module 8: Business rules & quarantine engine
│   ├── reporter.py                     # Module 9: JSON and responsive HTML report generators
│   └── pipeline.py                     # Modules 10-11: ETL orchestrator & rotating logging
│
├── scripts/
│   └── generate_sample_data.py         # Reproducible synthetic messy dataset generator
│
├── logs/
│   └── .gitkeep                        # Central directory for logs
│
├── tests/
│   ├── __init__.py
│   ├── test_loader.py                  # Ingestion & encoding tests
│   ├── test_currency.py                # Currency parsing tests
│   ├── test_dates.py                   # Date normalization & edge cases
│   ├── test_cleaning.py                # Missing values & deduplication tests
│   ├── test_schema.py                  # Schema transformation & casing tests
│   ├── test_validation.py              # Rule verification & quarantine tests
│   ├── test_edge_cases.py              # Boundary & empty DataFrame tests
│   └── test_pipeline.py                # End-to-end integration tests
│
├── main.py                             # Command-line interface (CLI) entry point
├── requirements.txt                    # Python project dependencies
├── .gitignore                          # Standard git exclusion rules
└── README.md                           # Project technical documentation
```

---

## 8. Installation & Setup (Windows CMD & PowerShell)

### Prerequisites
- Windows 10 or 11
- Python 3.11, 3.12, or 3.13 installed (Verify with `python --version`)
- Visual Studio Code or any code editor

### Step 1: Open Terminal in Project Root
Navigate to the project directory:
```cmd
cd "c:\Users\dell pc\Desktop\project2"
```

### Step 2: Create a Virtual Environment
```cmd
python -m venv venv
```

### Step 3: Activate the Virtual Environment
**On Windows Command Prompt (CMD):**
```cmd
venv\Scripts\activate.bat
```

**On Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```
*(If script execution is blocked on PowerShell, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once).*

### Step 4: Upgrade Pip & Install Dependencies
```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 9. How to Run the Application

The application provides both an **interactive Streamlit Web Dashboard (`app.py`)** and a flexible **Command-Line Interface (`main.py`)** powered by `argparse`.

### 1. Launch Interactive Streamlit Web UI (Recommended)
Launch the visual web dashboard to inspect raw data, run the ETL pipeline, view pass/quarantine splits, and download cleaned files:
```cmd
streamlit run app.py
```

### 2. Inspect & Profile Dataset via CLI (No Changes Made)
Inspect raw dimensions, missing rates, uniqueness, and IQR outliers before transforming:
```cmd
python main.py --input data/raw/sample_messy_data.csv --profile-only
```

### 3. Execute Full Pipeline via CLI (Default Configuration)
Run the end-to-end pipeline using the default configuration:
```cmd
python main.py
```

### 4. Run with Custom Paths and Verbose Debug Logging
```cmd
python main.py --input data/raw/sample_messy_data.csv --config config/schema_config.json --output data/output --verbose
```

### 5. CLI Arguments Reference
| Short Flag | Long Flag | Default | Description |
| :--- | :--- | :--- | :--- |
| `-i` | `--input` | `data/raw/sample_messy_data.csv` | Path to the source raw CSV file |
| `-c` | `--config` | `config/schema_config.json` | Path to JSON schema configuration |
| `-o` | `--output` | `data/output` | Output folder for clean data & reports |
| `-p` | `--profile-only`| `False` | Run inspection without modifying data |
| `-v` | `--verbose` | `False` | Enable DEBUG level output in terminal |

---

## 10. Sample Input vs. Output

### Raw Sample Input (`data/raw/sample_messy_data.csv`)
```csv
Cust_ID , Customer Name, Age,Email_Address ,Phone Number,Annual Income ,Join_Date,City ,Active Status,Notes
1001,Rahul Mehta,23,rahul.mehta45@example.com,+91-8051802512,"INR 93,513",15 Jan 2023,Bengaluru,0,
1004,Diya Singh,31,invalid-email-format,+91-8445662585,"₹61,793",2021-08-01,Bengaluru,FALSE,
1005,   ,24,saanvi.singh68@example.com,+91-9303082117,"Rs. 67,722",2023/01/15,Pune,0,
1010,Vivaan Rao,47,vivaan.rao44@example.com,+91-7284277889,"90,307.00",99/99/9999,Hyderabad,no,
1012,  Aadhya Bose  ,45,aadhya.bose38@example.com,+91-7594130308,"Rs. 168,569",2023/01/15,Mumbai,true,
1019,Rohan Chatterjee,-4,rohan.chatterjee79@example.com,+91-9962958940,"Rs 87,730.50",2024-05-10,Kolkata,0,
```

### Cleaned Valid Output (`data/output/cleaned_data.csv`)
```csv
customer_id,customer_name,age,email,phone,salary,joining_date,city,is_active
1001,Rahul Mehta,23,rahul.mehta45@example.com,+91-8051802512,93513.0,2023-01-15,Bengaluru,False
1012,Aadhya Bose,45,aadhya.bose38@example.com,+91-7594130308,168569.0,2023-01-15,Mumbai,True
...
```

### Quarantined Output with Reasons (`data/output/invalid_records.csv`)
```csv
customer_id,customer_name,age,email,phone,salary,joining_date,city,is_active,rejection_reasons
1004,Diya Singh,31,invalid-email-format,+91-8445662585,61793.0,2021-08-01,Bengaluru,False,Value 'invalid-email-format' in 'email' does not match pattern '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
1005,,24,saanvi.singh68@example.com,+91-9303082117,67722.0,2023-01-15,Pune,False,Missing mandatory field 'customer_name'
1010,Vivaan Rao,47,vivaan.rao44@example.com,+91-7284277889,90307.0,,Hyderabad,False,Missing mandatory field 'joining_date'
1019,Rohan Chatterjee,-4,rohan.chatterjee79@example.com,+91-9962958940,87730.5,2024-05-10,Kolkata,False,Value -4 in 'age' is below minimum threshold (18)
```

---

## 11. Automated Testing Instructions

The test suite covers positive scenarios, negative edge cases, corrupt files, empty tables, and full pipeline integration.

### Run All Tests via Pytest
```cmd
pytest
```

### Run with Detailed Verbosity and Execution Times
```cmd
pytest -v --durations=5
```

### Expected Test Result:
```
tests/test_cleaning.py::test_missing_values_imputation PASSED            [  3%]
tests/test_cleaning.py::test_duplicate_handler_exact_and_subset PASSED   [  6%]
tests/test_currency.py::test_clean_currency_string_valid PASSED          [ 45%]
tests/test_dates.py::test_date_normalizer_various_formats PASSED         [ 54%]
tests/test_dates.py::test_date_normalizer_invalid_dates PASSED           [ 58%]
tests/test_edge_cases.py::test_empty_dataframe_profiler PASSED           [ 61%]
tests/test_pipeline.py::test_pipeline_end_to_end PASSED                  [ 90%]
tests/test_validation.py::test_validation_rules_segregation PASSED       [100%]
============================= 31 passed in 1.94s ==============================
```

---

## 12. Explanation of Validation Reports

1. **`validation_report.json`**:
   - Machine-parseable JSON payload containing end-to-end metrics.
   - Contains: `original_record_count`, `final_clean_record_count`, `quarantined_record_count`, `duplicates_removed_count`, `missing_values_handled_count`, initial profiling breakdown, currency symbols extracted, and column-by-column dtype transitions (`from` -> `to`).
2. **`cleaning_summary.html`**:
   - Modern, zero-dependency visual report viewable in any web browser.
   - Includes stat metric cards, color-coded pass/fail badges, schema evolution tables, and rule violation tallies.
   - Ideal for attaching to stakeholder emails or demonstrating in project evaluations.
3. **`cleaning.log`**:
   - Detailed event trace recorded using `RotatingFileHandler` with millisecond timestamps, logger namespaces, and severity levels (`INFO`, `WARNING`, `ERROR`).

---

## 13. System Limitations

- **In-Memory Scale**: The pipeline currently leverages Pandas in-memory DataFrames, making it optimal for datasets up to ~2-4 GB depending on available RAM. For petabyte-scale streaming, a distributed engine like PySpark or Polars is recommended.
- **Fixed Exchange Rates**: The currency normalizer cleans and standardizes currency tokens (e.g. `₹`, `Rs`, `INR`) and converts to floating-point numbers. It does not perform dynamic live currency exchange rate conversions unless explicitly integrated with a Forex API.

---

## 14. Future Improvements

1. **Multi-File Batch & Directory Watcher**: Extend the CLI to ingest entire directories of CSV files in batch mode using `multiprocessing`.
2. **Parquet & Delta Lake Support**: Add dual-export targets to columnar formats (`.parquet`) with Snappy compression for data warehouse ingestion.
3. **Great Expectations Integration**: Incorporate declarative Great Expectations suites for enterprise contract validation.
4. **Airflow / Prefect Operator**: Package the pipeline into an Apache Airflow custom operator for scheduled DAG workflow execution.
