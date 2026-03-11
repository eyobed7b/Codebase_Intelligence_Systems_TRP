# The Brownfield Cartographer 🗺️

Engineering Codebase Intelligence Systems for Rapid FDE Onboarding in Production Environments.

The Brownfield Cartographer is a multi-agent system designed to ingest unfamiliar, complex codebases and produce a living, queryable knowledge graph of architecture, data flows, and semantic purpose.

## 🚀 Quick Start

### 1. Prerequisites

- [uv](https://github.com/astral-sh/uv) (Recommended) or Python 3.11+
- Git

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Codebase_Intelligence_Systems_TRP

# Install dependencies using uv
uv sync
```

### 3. Run Analysis

Point the Cartographer at any local repository or directory.

```bash
uv run src/cli.py analyze /path/to/target/repo
```

Artifacts will be generated in the `.cartography/` directory.

### 4. Query the System

Query the generated knowledge graph (experimental).

```bash
uv run src/cli.py query /path/to/target/repo "Where is the ingestion logic?"
```

## 🏗️ Architecture

The Cartographer is designed as a modular, multi-agent pipeline that can be pointed at an arbitrary codebase. Its high-level architecture looks like this:

```
+------------------+    +------------------+    +------------------+
|   Surveyor Agent  | -> |  Hydrologist      | -> |  Semanticist      |
|  (static analysis)|    |  Agent (lineage)  |    |  Agent (LLM)      |
+------------------+    +------------------+    +------------------+
           |                     |                     |
           v                     v                     v
      module_graph.json     lineage_graph.json   semantic_tags.json
                              |                     |
                              +---------+-----------+
                                        v
                                Archivist Agent
                             (artifact assembly &
                           living context maintenance)
                                        |
                                        v
                             .cartography/ (output folder)

```

Each agent is implemented as a standalone Python class within `src/agents/` and communicates via well-defined JSON artifacts stored temporarily in `.cartography/`.

1. **The Surveyor (Static Structure)**
   - Uses `tree-sitter` for language-agnostic AST parsing.
   - Builds import/function call graphs, identifies public APIs, and computes change velocity using Git history.

2. **The Hydrologist (Data Lineage)**
   - Constructs data lineage DAGs by analyzing SQL (via `sqlglot`), Python (Pandas/SQLAlchemy/PySpark), YAML/JSON configs (Airflow, dbt, Prefect), and Jupyter notebooks.
   - Python scanning captures:
     - pandas I/O (`read_csv`, `to_parquet`, etc.)
     - SQLAlchemy/DBAPI executions (`session.execute`, `hook.run`, `cursor.execute`).
     - PySpark `.read` / `.write` patterns and `load`/`save` calls.
     - Any embedded SQL is parsed with sqlglot and emitted as separate transformation nodes.
   - Notebook (`.ipynb`) cells are concatenated and processed as Python code to extract the same patterns.
   - YAML/JSON configs are walked for `sql`/`query` strings, dbt `ref()` calls, and even `name` fields (to seed dataset nodes).
   - Artifacts produced: `lineage_graph.json` with a NetworkX DiGraph containing dataset nodes and transformation edges annotated with `transformation_type`, `source_file`, and `line_range`. Useful queries include "upstream dependencies of table X" or "what breaks if table Y changes"; the `Hydrologist` class even has `upstream_dependencies()`/`downstream_dependencies()` helpers for these lookups.

3. **The Semanticist (LLM Analysis)**
   - Generates business-level purpose statements for every module, detecting "documentation drift".
   - Clusters modules into functional domains and tags them in `semantic_tags.json`.

4. **The Archivist (Living Context)**
   - Consumes artifacts from the other agents to produce final deliverables such as `CODEBASE.md` (for AI agent injection) and `onboarding_brief.md`.
   - Keeps the `.cartography/` directory up-to-date and handles incremental re-runs.

These agents can be executed sequentially via the CLI (`src/cli.py`) or imported into other workflows. The design emphasizes easy extension; new analyzers or output writers can be dropped into the `src/agents/` or `src/analyzers/` packages respectively.

## 📄 Key Artifacts

The system produces several artifacts in the `.cartography/` directory:

- **`CODEBASE.md`**: A dense, structured context file containing the architectural overview, critical paths, and module index.
- **`onboarding_brief.md`**: Answers to the Five FDE Day-One Questions with evidence citations.
- **`module_graph.json`**: Serialized NetworkX graph of imports and function calls.
- **`lineage_graph.json`**: Serialized data flow dependencies.

## 🛠️ Supported Technologies

- **Languages**: Python, SQL (Multiple dialects via sqlglot), YAML, JSON.

## 🧪 Testing

A small pytest suite verifies Hydrologist patterns (pandas, SQLAlchemy, PySpark,
notebooks, and SQL files). Run the tests via the project virtualenv:

```bash
python -m pytest tests/test_hydrologist.py -q
```

- **Frameworks**: Airflow, dbt, Pandas.
- **Intelligence**: tree-sitter, PageRank, LLMs (Gemini Flash/Pro).

---

_Built for the 10Academy FDE TRP Week 4 Challenge._
