# RECONNAISSANCE.md - The Brownfield Cartographer

## Target Codebase: DE_challeneg_Airflow_PG_superset

**Repository:** `https://github.com/eyobed7b/DE_challeneg_Airflow_PG_superset.git`

---

### The Five FDE Day-One Answers (Manual Analysis)

#### 1. What is the primary data ingestion path?

The primary data ingestion path is from local files located in a source directory (configured as `/opt/tmp/`). The `extract_data` function in `de_etl.py` uses Pandas and standard Python file I/O to read three primary sources:

- `banking_marketing.csv` (CSV)
- `student_loan_2009_2010.csv` (CSV)
- `world_bank_indicators.json` (JSON)

#### 2. What are the 3-5 most critical output datasets/endpoints?

- **`ml.fact_banking_campaign`**: The largest fact table containing client interaction data and marketing results.
- **`ml.fact_student_loan`**: Aggregated loan figures by academic year and school.
- **`ml.report_marketing_metrics`**: An analytical report table derived from the filtered banking campaign data.
- **`ml.fact_indicator_value`**: (Indirectly critical) Target for the World Bank indicators transformation.

#### 3. What is the blast radius if the most critical module fails?

The most critical module is **`de_etl.py`**, which contains the entire DAG definition and ETL logic.

- **Entry point failure (`extract_data`)**: If this function fails (e.g., missing local files), the entire pipeline stalls. No downstream tasks (cleaning, transforming, loading) will execute.
- **Storage handler failure (`WarehouseLoader`)**: If this class or its `_execute_insert_rows` method breaks, no data will be written to the PostgreSQL data warehouse, though cleaning tasks might still succeed in isolation.

#### 4. Where is the business logic concentrated vs. distributed?

Business logic is **concentrated** within `de_etl.py`. Each transformation step is encapsulated in a dedicated Python function:

- **`clean_banking_data`**: Handles data type conversion, column renaming, and standardizing categorical values ('unknown' -> 'unknown_group').
- **`clean_student_loan_data`**: Implements unpivoting (melting) and aggregation from a wide format to a long format.
- **`flatten_and_clean_world_bank_data`**: Custom logic to flatten deeply nested JSON into relational format.
- **`run_analytical_transformations`**: Contains the logic for the final marketing KPI calculations (`conversion_rate`).

#### 5. What has changed most frequently in the last 90 days (git velocity map)?

Based on manual inspection of the git history, the project is relatively new (last commits in Dec 2025). The most frequently changed file appears to be:

- **`README.md`**: (4 commits) Documentation updates and setup instructions.
- All other files (`de_etl.py`, `tables.sql`) were added in the initial commit and haven't seen significant structural changes yet.

---

### Difficulty Analysis

**What was hardest to figure out manually?**

- **Data Lineage:** Determining which Python function feeds into which database table required cross-referencing XCom pulls in the loading task (`load_all_data_to_warehouse`) with the return values of the transformation tasks.
- **DB Schema vs. Code:** Some tables referenced in the code (like `ml.fact_indicator_value`) were not explicitly defined in the `tables.sql` file provided, leading to ambiguity about the actual warehouse state.
- **Hidden Config:** The `DATA_DIR` and `POSTGRES_CONN_ID` are hardcoded in the script, making it less obvious how the environment is configured without reading the file.

**Where did you get lost?**

- Tracking the `World Bank` data flattening was the most cognitively taxing part, as it involved three levels of nested dictionaries and specific column renaming.
- Understanding the `student_loan` melting logic required mentally simulating the transformation of columns like `Disbursements Q1`, `Q2`, etc., into a normalized format.
