# THE BROWNFIELD CARTOGRAPHER - INTERIM SUBMISSION REPORT

**Date:** March 11, 2026  
**Subject:** Codebase Intelligence System for Rapid FDE Onboarding

---

## 📸 1. Architecture Diagram

![The Brownfield Cartographer Architecture](cartographer_architecture_diagram_1773242617654.png)

The system is designed as a modular, four-agent pipeline that transforms raw source code into a living, queryable knowledge graph.

---

## 🔍 2. RECONNAISSANCE.md (Manual Analysis)

### Target Codebase: DE_challeneg_Airflow_PG_superset

**Repository:** `https://github.com/eyobed7b/DE_challeneg_Airflow_PG_superset.git`

#### The Five FDE Day-One Answers

1. **Primary data ingestion path?**
   - Local files in `/opt/tmp/`. The `extract_data` function in `de_etl.py` reads `banking_marketing.csv`, `student_loan_2009_2010.csv`, and `world_bank_indicators.json`.
2. **Critical output datasets?**
   - `ml.fact_banking_campaign`, `ml.fact_student_loan`, and `ml.report_marketing_metrics`.
3. **Blast radius of critical module?**
   - **`de_etl.py`** failure stalls the entire pipeline. Missing ingestion files cause immediate upstream failure.
4. **Concentration of Business Logic?**
   - Concentrated in `de_etl.py` within specific cleaning functions (`clean_banking_data`, `flatten_and_clean_world_bank_data`).
5. **Change Velocity (Last 90 Days)?**
   - High activity on `README.md` for documentation; core ETL logic has remained stable since initial commit.

---

## 📈 3. Progress Summary

| Component              | Status         | Description                                                                                                     |
| :--------------------- | :------------- | :-------------------------------------------------------------------------------------------------------------- |
| **Surveyor Agent**     | ✅ Working     | Extracts AST structure, imports, and public APIs using `tree-sitter`. Handles Git-less environments gracefully. |
| **Hydrologist Agent**  | 🟡 In Progress | Extracts SQL lineage and basic code-level data flows. Currently refining regex for variable-based paths.        |
| **Semanticist Agent**  | ✅ Working     | LLM-powered business purpose extraction. Supports Gemini, OpenAI, and Groq.                                     |
| **Archivist Agent**    | ✅ Working     | Assembles JSON artifacts into human-readable `CODEBASE.md`.                                                     |
| **CLI & Orchestrator** | ✅ Working     | Unified interface for analysis and GitHub repo cloning.                                                         |

---

## 🔭 4. Early Accuracy Observations

### Module Graph Accuracy: **High**

The Surveyor correctly identified the Airflow DAG structure, mapping the relationship between the ETL script (`de_etl.py`) and the DDL schema (`tables.sql`). Complexity scores accurately highlight the ETL script as the "hub" of the system.

### Lineage Graph Accuracy: **Medium**

The system perfectly extracted the schema dependencies from the SQL files. However, it currently misses the direct link between Python Pandas operations and the SQL tables because the target codebase uses variable-based path definitions (e.g., `pd.read_csv(BANKING_CSV_LOCAL)`). This is a known limitation of regex-based scanning.

---

## 🚧 5. Known Gaps & Final Submission Plan

### Identified Gaps

1. **Dynamic Path Analysis**: Current regex fails on variables. Need static value tracking or LLM-assisted lineage resolution.
2. **Airflow XCom Logic**: The data flow between Python functions is passed via XCom, which requires specific Airflow-aware tracing.
3. **Blast Radius Visuals**: We have the data, but no interactive visualization for the impact analysis yet.

### Plan for Final Submission

- **Week 4 Final**: Implement a "Semantic Lineage Binder" that uses the Semanticist to bridge gaps in static data flow analysis.
- **Refinement**: Improve Airflow operator parsing to better understand source/sink relationships in DAGs.
- **Reporting**: Finalize a multi-format export (JSON, Markdown, and formal PDF summary).

---

_Built for the 10Academy FDE TRP Week 4 Challenge._
