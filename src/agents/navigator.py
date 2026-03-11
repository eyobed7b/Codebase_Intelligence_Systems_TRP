import networkx as nx
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

class NavigatorTools:
    def __init__(self, module_graph: nx.DiGraph, lineage_graph: nx.DiGraph):
        self.module_graph = module_graph
        self.lineage_graph = lineage_graph

    @tool
    def find_implementation(self, concept: str) -> str:
        """Semantic search for where a concept (e.g. 'revenue', 'ingestion') is implemented."""
        # Simple search in node logic for now
        # Ideally, we'd use vector search here
        matches = []
        for node, data in self.module_graph.nodes(data=True):
            if concept.lower() in node.lower() or concept.lower() in str(data.get("purpose_statement", "")).lower():
                matches.append(node)
        
        if not matches:
            return f"No direct implementation of '{concept}' found."
        return f"Implementation of '{concept}' likely matches: {', '.join(matches[:5])}"

    @tool
    def trace_lineage(self, ds_name: str, direction: str = "upstream") -> str:
        """Trace the data lineage for a dataset. direction 'upstream' or 'downstream'."""
        ds_id = f"ds:{ds_name}"
        if ds_id not in self.lineage_graph:
            return f"Dataset '{ds_name}' not found in lineage graph."
        
        if direction == "upstream":
            paths = nx.ancestors(self.lineage_graph, ds_id)
            return f"Upstream dependencies for '{ds_name}': {', '.join(paths)}"
        else:
            paths = nx.descendants(self.lineage_graph, ds_id)
            return f"Downstream dependencies for '{ds_name}': {', '.join(paths)}"

    @tool
    def blast_radius(self, module_path: str) -> str:
        """Determine what breaks if a module's interface is changed."""
        if module_path not in self.module_graph:
            return f"Module '{module_path}' not found."
            
        descendants = nx.descendants(self.module_graph, module_path)
        return f"Blast radius of changing '{module_path}': {', '.join(descendants)}"

    @tool
    def explain_module(self, path: str) -> str:
        """Retrieve the semantic purpose and signature of a module."""
        if path not in self.module_graph:
            return f"Module '{path}' not found."
            
        data = self.module_graph.nodes[path]
        return f"Module: {path}\nPurpose: {data.get('purpose_statement', 'N/A')}\nLanguage: {data.get('language')}"
