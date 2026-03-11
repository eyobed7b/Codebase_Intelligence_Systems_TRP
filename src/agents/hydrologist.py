import os
import networkx as nx
from typing import List, Dict, Any, Tuple, Set
from src.analyzers.sql_lineage import SQLLineageAnalyzer
from src.analyzers.dag_config_parser import DAGConfigParser
from src.models.node import DatasetNode, TransformationNode, StorageType
import yaml

class Hydrologist:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.sql_analyzer = SQLLineageAnalyzer()
        self.config_parser = DAGConfigParser()
        self.lineage_graph = nx.DiGraph()
        self.nodes = {}

    def analyze(self):
        """Analyze data flows across Python, SQL, and YAML."""
        for root, dirs, files in os.walk(self.repo_path):
            if ".git" in root:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.repo_path)
                
                if file.endswith(".sql"):
                    self._analyze_sql(file_path, rel_path)
                elif file.endswith(".py"):
                    self._analyze_python(file_path, rel_path)
                elif file.endswith((".yaml", ".yml")):
                    self._analyze_config(file_path, rel_path)
                elif file.endswith(".ipynb"):
                    self._analyze_notebook(file_path, rel_path)

    def _analyze_sql(self, file_path: str, rel_path: str):
        with open(file_path, "r") as f:
            content = f.read()
            lineage = self.sql_analyzer.extract_lineage(content)
            
            # Create transformation node
            trans_id = f"trans:{rel_path}"
            trans_node = TransformationNode(
                id=trans_id,
                source_datasets=lineage["sources"],
                target_datasets=lineage["targets"],
                transformation_type="sql",
                source_file=rel_path,
                line_range=(1, len(content.splitlines())),
                sql_query_if_applicable=content
            )
            self.nodes[trans_id] = trans_node
            self.lineage_graph.add_node(trans_id, **trans_node.model_dump())
            
            # Create dataset nodes and edges
            for s in lineage["sources"]:
                ds_id = f"ds:{s}"
                if ds_id not in self.nodes:
                    self.nodes[ds_id] = DatasetNode(id=ds_id, name=s, storage_type=StorageType.TABLE)
                    self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                self.lineage_graph.add_edge(ds_id, trans_id)
                
            for t in lineage["targets"]:
                ds_id = f"ds:{t}"
                if ds_id not in self.nodes:
                    self.nodes[ds_id] = DatasetNode(id=ds_id, name=t, storage_type=StorageType.TABLE)
                    self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                self.lineage_graph.add_edge(trans_id, ds_id)

    def _analyze_python(self, file_path: str, rel_path: str):
        # high‑level transformation node representing this Python script; added only
        # if we detect at least one data interaction
        trans_id = f"trans:{rel_path}"
        has_trans_node = False

        def ensure_trans_node(content: str):
            nonlocal has_trans_node
            if not has_trans_node:
                trans_node = TransformationNode(
                    id=trans_id,
                    source_datasets=[],
                    target_datasets=[],
                    transformation_type="python",
                    source_file=rel_path,
                    line_range=(1, len(content.splitlines())),
                )
                self.nodes[trans_id] = trans_node
                self.lineage_graph.add_node(trans_id, **trans_node.model_dump())
                has_trans_node = True

        # Extract pandas read/write calls using grep/simple search for now
        # Ideally, we'd use tree-sitter here too
        import re
        with open(file_path, "r") as f:
            content = f.read()
            
            # Simple patterns for pandas read_csv, read_sql, etc. (Handles both strings and variable names)
            read_patterns = re.findall(r"pd\.read_(csv|sql|json|parquet|table)\((?:path=|filepath_or_buffer=)?(['\"].+?['\"]|[\w_]+)(?:,.*)?\)", content)
            write_patterns = re.findall(r"\.to_(csv|sql|json|parquet)\((?:path_or_buf=)?(['\"].+?['\"]|[\w_]+)(?:,.*)?\)", content)

            # PySpark read/write, rudimentary capture
            spark_read = re.findall(r"spark\.read(?:\.format\([^\)]+\))?\.(csv|json|parquet|table|jdbc)\((['\"].+?['\"]|[\w_]+)\)", content)
            spark_load = re.findall(r"spark\.read\.load\((['\"].+?['\"]|[\w_]+)\)", content)
            spark_write = re.findall(r"\.write\.(csv|json|parquet|save|jdbc|saveAsTable)\((['\"].+?['\"]|[\w_]+)\)", content)

            # Custom WarehouseLoader pattern (Specific to the target challenge)
            # loader.load_dataframe(df, 'table_name', ...)
            custom_loads = re.findall(r"\.load_dataframe\(.+?,\s*(['\"].+?['\"]|[\w_]+)", content)

            # SQLAlchemy execute calls we should also inspect
            sqlalchemy_exec = re.findall(r"(?:session\.|engine\.)execute\((?:f)?([\"'])([\s\S]*?)\1\)", content)

            # hooks/operators invoking SQL via `run` or `execute` (e.g. PostgresHook)
            sql_call_patterns = re.findall(
                r"(?:hook\.|self\.hook\.|PostgresHook\([^\)]*\)\.)"
                r"run\((?:f)?([\"'])([\s\S]*?)\1\)",
                content,
            )
            execute_patterns = re.findall(
                r"(?:cursor\.|hook\.|self\.hook\.)execute\((?:f)?([\"'])([\s\S]*?)\1\)",
                content,
            )

            for _, path in read_patterns:
                ds_name = path.strip('"\'')
                ds_id = f"ds:{ds_name}"
                if ds_id not in self.nodes:
                    self.nodes[ds_id] = DatasetNode(id=ds_id, name=ds_name, storage_type=StorageType.FILE)
                    self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                ensure_trans_node(content)
                self.lineage_graph.add_edge(ds_id, trans_id)

            for _, path in write_patterns:
                ds_name = path.strip('"\'')
                ds_id = f"ds:{ds_name}"
                if ds_id not in self.nodes:
                    self.nodes[ds_id] = DatasetNode(id=ds_id, name=ds_name, storage_type=StorageType.FILE)
                    self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                ensure_trans_node(content)
                self.lineage_graph.add_edge(trans_id, ds_id)

            # spark reads
            for _, path in spark_read + spark_load:
                ds_name = path.strip('"\'')
                ds_id = f"ds:{ds_name}"
                if ds_id not in self.nodes:
                    self.nodes[ds_id] = DatasetNode(id=ds_id, name=ds_name, storage_type=StorageType.FILE)
                    self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                ensure_trans_node(content)
                self.lineage_graph.add_edge(ds_id, trans_id)

            # spark writes
            for _, path in spark_write:
                ds_name = path.strip('"\'')
                ds_id = f"ds:{ds_name}"
                if ds_id not in self.nodes:
                    self.nodes[ds_id] = DatasetNode(id=ds_id, name=ds_name, storage_type=StorageType.FILE)
                    self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                ensure_trans_node(content)
                self.lineage_graph.add_edge(trans_id, ds_id)

            # custom loader writes (WarehouseLoader)
            for ds_name in custom_loads:
                ds_name = ds_name.strip('"\'')
                ds_id = f"ds:{ds_name}"
                if ds_id not in self.nodes:
                    self.nodes[ds_id] = DatasetNode(id=ds_id, name=ds_name, storage_type=StorageType.TABLE)
                    self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                ensure_trans_node(content)
                self.lineage_graph.add_edge(trans_id, ds_id)

            # process SQL strings found in hook.run, execute calls, or SQLAlchemy executions
            for _, sql_text in sql_call_patterns + execute_patterns + sqlalchemy_exec:
                try:
                    lineage = self.sql_analyzer.extract_lineage(sql_text)
                except Exception:
                    continue
                ensure_trans_node(content)
                # create a synthetic transformation node for this SQL snippet
                sql_trans_id = f"trans:{rel_path}:sql"
                trans_node = TransformationNode(
                    id=sql_trans_id,
                    source_datasets=lineage.get("sources", []),
                    target_datasets=lineage.get("targets", []),
                    transformation_type="sql",
                    source_file=rel_path,
                    line_range=(1, len(sql_text.splitlines())),
                    sql_query_if_applicable=sql_text,
                )
                self.nodes[sql_trans_id] = trans_node
                self.lineage_graph.add_node(sql_trans_id, **trans_node.model_dump())
                for s in lineage.get("sources", []):
                    ds_id = f"ds:{s}"
                    if ds_id not in self.nodes:
                        self.nodes[ds_id] = DatasetNode(id=ds_id, name=s, storage_type=StorageType.TABLE)
                        self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                    self.lineage_graph.add_edge(ds_id, sql_trans_id)
                for t in lineage.get("targets", []):
                    ds_id = f"ds:{t}"
                    if ds_id not in self.nodes:
                        self.nodes[ds_id] = DatasetNode(id=ds_id, name=t, storage_type=StorageType.TABLE)
                        self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
                    self.lineage_graph.add_edge(sql_trans_id, ds_id)

    def _analyze_config(self, file_path: str, rel_path: str):
        # Specific logic for Airflow DAGs or dbt config using DAGConfigParser
        config = None
        if file_path.endswith((".yaml", ".yml")):
            config = self.config_parser.parse_yaml(file_path)
        elif file_path.endswith(".json"):
            config = self.config_parser.parse_json(file_path)

        if not config:
            return

        # Extract SQL
        sql_fragments = self.config_parser.extract_sql_fragments(config)
        for sql in sql_fragments:
            self._register_sql_fragment(sql, rel_path)

        # Extract Dataset names
        dataset_names = self.config_parser.extract_dataset_names(config)
        for name in dataset_names:
            ds_id = f"ds:{name}"
            if ds_id not in self.nodes:
                self.nodes[ds_id] = DatasetNode(id=ds_id, name=name, storage_type=StorageType.TABLE)
                self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())

    def blast_radius(self, dataset_id: str) -> int:
        """Return the number of downstream nodes affected by this dataset."""
        if dataset_id not in self.lineage_graph:
            return 0
        return len(nx.descendants(self.lineage_graph, dataset_id))

    def find_sources(self, node_id: str) -> List[str]:
        """Return all upstream data sources for a given node."""
        if node_id not in self.lineage_graph:
            return []
        return list(nx.ancestors(self.lineage_graph, node_id))

    def find_sinks(self, node_id: str) -> List[str]:
        """Return all downstream data sinks for a given node."""
        if node_id not in self.lineage_graph:
            return []
        return list(nx.descendants(self.lineage_graph, node_id))

    def _analyze_notebook(self, file_path: str, rel_path: str):
        """Scan .ipynb for code cells and delegate to python analyzer."""
        try:
            import json
            with open(file_path, "r") as f:
                nb = json.load(f)
        except Exception:
            return

        # concatenate all code cells and run through the python analyzer
        code_cells = []
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                source = "".join(cell.get("source", []))
                code_cells.append(source)
        if not code_cells:
            return

        # write a temporary string to pass to _analyze_python logic
        joined = "\n".join(code_cells)
        # we'll cheat by creating a fake file_path context so that line numbers
        # still make sense (they will all be 1..len(joined)).
        # create a small wrapper that reads from the string instead of disk
        # for simplicity, we'll call _analyze_python on a temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tmp:
            tmp.write(joined)
            tmp.flush()
            self._analyze_python(tmp.name, rel_path + "[ipynb]")
        # Note: temp file is left on disk; OS will clean eventually

    def _register_sql_fragment(self, sql_text: str, rel_path: str):
        # helper to register a small SQL snippet found in configs
        lineage = self.sql_analyzer.extract_lineage(sql_text)
        if not lineage:
            return
        trans_id = f"trans:{rel_path}:sqlcfg"
        trans_node = TransformationNode(
            id=trans_id,
            source_datasets=lineage.get("sources", []),
            target_datasets=lineage.get("targets", []),
            transformation_type="sql",
            source_file=rel_path,
            line_range=(1, len(sql_text.splitlines())),
            sql_query_if_applicable=sql_text,
        )
        self.nodes[trans_id] = trans_node
        self.lineage_graph.add_node(trans_id, **trans_node.model_dump())
        for s in lineage.get("sources", []):
            ds_id = f"ds:{s}"
            if ds_id not in self.nodes:
                self.nodes[ds_id] = DatasetNode(id=ds_id, name=s, storage_type=StorageType.TABLE)
                self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
            self.lineage_graph.add_edge(ds_id, trans_id)
        for t in lineage.get("targets", []):
            ds_id = f"ds:{t}"
            if ds_id not in self.nodes:
                self.nodes[ds_id] = DatasetNode(id=ds_id, name=t, storage_type=StorageType.TABLE)
                self.lineage_graph.add_node(ds_id, **self.nodes[ds_id].model_dump())
            self.lineage_graph.add_edge(trans_id, ds_id)

    def get_results(self):
        return {
            "nodes": [n.model_dump() for n in self.nodes.values()],
            "graph": nx.node_link_data(self.lineage_graph)
        }

    # utility helpers -------------------------------------------------------
    def upstream_dependencies(self, table_name: str) -> Set[str]:
        """Return a set of dataset ids that flow into the given table."""
        ds_id = f"ds:{table_name}"
        if ds_id not in self.lineage_graph:
            return set()
        return nx.ancestors(self.lineage_graph, ds_id)

    def downstream_dependencies(self, table_name: str) -> Set[str]:
        """Return a set of dataset ids that depend on the given table."""
        ds_id = f"ds:{table_name}"
        if ds_id not in self.lineage_graph:
            return set()
        return nx.descendants(self.lineage_graph, ds_id)
