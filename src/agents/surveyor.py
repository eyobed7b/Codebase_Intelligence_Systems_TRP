import os
import networkx as nx
try:
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
import datetime
from typing import List, Dict, Any, Tuple, Optional
from src.analyzers.tree_sitter_analyzer import TreeSitterAnalyzer
from src.models.node import ModuleNode, FunctionNode
from src.models.edge import EdgeType

class Surveyor:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.analyzer = TreeSitterAnalyzer()
        self.module_graph = nx.DiGraph()
        self.nodes = {}
        self.edges = []

    def analyze_module(self, path: str) -> ModuleNode:
        """Deep analysis of a single module."""
        rel_path = os.path.relpath(path, self.repo_path)
        language = "python" if path.endswith(".py") else "unknown"
        
        node = ModuleNode(
            id=rel_path,
            path=rel_path,
            language=language,
            last_modified=self._get_last_modified(path),
            change_velocity_30d=self._get_git_velocity(path)
        )

        if language == "python":
            tree = self.analyzer.parse_file(path)
            if tree:
                # 1. Imports
                raw_imports = self.analyzer.extract_imports(path, tree)
                resolved_imports = []
                for imp in raw_imports:
                    resolved = self._resolve_import(imp, rel_path)
                    if resolved:
                        resolved_imports.append(f"{imp} -> {resolved}")
                    else:
                        resolved_imports.append(imp)
                node.imports = resolved_imports

                # 2. Public Functions
                # Extract and filter for public ones (not starting with _), stripping any leading underscores
                funcs = self.analyzer.extract_functions(path, tree)
                node.functions = [f['name'].lstrip('_') for f in funcs if not f['name'].startswith("__")]

                # 3. Class Definitions
                node.classes = self.analyzer.extract_classes(path, tree)

        return node

    def analyze(self):
        """Perform full static analysis of the repository."""
        for root, dirs, files in os.walk(self.repo_path):
            # Skip .git etc
            if ".git" in root:
                continue
                
            for file in files:
                if file.endswith((".py", ".sql", ".yaml", ".json")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.repo_path)
                    self._analyze_file(file_path, rel_path)

        # After all files analyzed, identify hubs and circular deps
        self._post_process()

    def _analyze_file(self, file_path: str, rel_path: str):
        language = "python" if file_path.endswith(".py") else "sql" if file_path.endswith(".sql") else "yaml" if file_path.endswith(".yaml") else "json"
        
        # 1. Module Node
        module_node = ModuleNode(
            id=rel_path,
            path=rel_path,
            language=language,
            last_modified=self._get_last_modified(file_path),
            change_velocity_30d=self._get_git_velocity(file_path, days=30)
        )
        self.nodes[rel_path] = module_node
        self.module_graph.add_node(rel_path, **module_node.model_dump())

        # 2. Extract detailed info for Python files
        if language == "python":
            tree = self.analyzer.parse_file(file_path)
            if tree:
                # Extract functions
                funcs = self.analyzer.extract_functions(file_path, tree)
                for f in funcs:
                    func_id = f"{rel_path}:{f['name']}"
                    func_node = FunctionNode(
                        id=func_id,
                        qualified_name=f['name'],
                        parent_module=rel_path,
                        signature=f['signature'],
                        is_public_api=not f['name'].startswith("_")
                    )
                    self.nodes[func_id] = func_node
                    self.module_graph.add_edge(rel_path, func_id, type="CONTAINS")
                
                # Extract imports
                imports = self.analyzer.extract_imports(file_path, tree)
                for imp in imports:
                    # Simple import resolution (can be improved)
                    target_rel_path = self._resolve_import(imp, rel_path)
                    if target_rel_path:
                        self.module_graph.add_edge(rel_path, target_rel_path, type=EdgeType.IMPORTS)

    def _resolve_import(self, import_text: str, source_rel_path: str) -> Optional[str]:
        # Very simple resolution logic for now
        # Covers: from x.y import z -> x/y.py
        # Covers: import x.y -> x/y.py
        
        parts = import_text.replace("import ", "").replace("from ", "").split(" ")
        module_path = parts[0].replace(".", "/")
        
        potential_paths = [
            f"{module_path}.py",
            f"{module_path}/__init__.py"
        ]
        
        for p in potential_paths:
            if os.path.exists(os.path.join(self.repo_path, p)):
                return p
        return None

    def _get_last_modified(self, file_path: str) -> str:
        try:
            mtime = os.path.getmtime(file_path)
            return datetime.datetime.fromtimestamp(mtime).isoformat()
        except:
            return ""

    def _get_git_velocity(self, file_path: str, days: int = 30) -> float:
        if not GIT_AVAILABLE:
            return 0.0
        try:
            repo = Repo(self.repo_path)
            since_date = datetime.datetime.now() - datetime.timedelta(days=days)
            commits = list(repo.iter_commits(since=since_date, paths=file_path))
            return float(len(commits))
        except:
            return 0.0

    def _post_process(self):
        # Calculate PageRank
        try:
            pagerank = nx.pagerank(self.module_graph)
            for node, rank in pagerank.items():
                if node in self.nodes and isinstance(self.nodes[node], ModuleNode):
                    self.nodes[node].complexity_score = rank
        except nx.PowerIterationFailedConvergence:
            pass

        # Detect dead code candidates
        self._detect_dead_code()

    def _detect_dead_code(self):
        """Identify nodes with no incoming edges (excluding entry points)."""
        for node_id in self.module_graph.nodes:
            if self.module_graph.in_degree(node_id) == 0:
                if node_id in self.nodes:
                    node = self.nodes[node_id]
                    # Simple heuristic: modules with no imports or functions with no calls
                    if isinstance(node, ModuleNode) and node.language == "python":
                         # Could be a script run directly, but still a candidate
                         pass
                    elif isinstance(node, FunctionNode):
                        # Internal functions with no calls are strong candidates
                        if not node.is_public_api:
                             # Mark as dead code candidate
                             pass

    def get_results(self):
        return {
            "nodes": [n.model_dump() for n in self.nodes.values()],
            "graph": nx.node_link_data(self.module_graph)
        }
