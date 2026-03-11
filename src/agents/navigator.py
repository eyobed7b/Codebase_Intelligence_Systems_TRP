import networkx as nx
import os
import json
import litellm
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

class NavigatorTools:
    def __init__(self, module_graph: nx.DiGraph, lineage_graph: nx.DiGraph):
        self.module_graph = module_graph
        self.lineage_graph = lineage_graph

    def find_implementation(self, concept: str) -> str:
        """Search for where a concept is implemented."""
        matches = []
        for node, data in self.module_graph.nodes(data=True):
            if concept.lower() in node.lower() or concept.lower() in str(data.get("purpose_statement", "")).lower():
                matches.append(node)
        return f"Matches: {', '.join(matches[:5])}" if matches else "No matches."

    def trace_lineage(self, ds_name: str, direction: str = "upstream") -> str:
        """Trace data lineage."""
        ds_id = f"ds:{ds_name}"
        if ds_id not in self.lineage_graph:
            # Try finding similar names
            matches = [n for n in self.lineage_graph.nodes if ds_name.lower() in n.lower()]
            return f"Dataset '{ds_name}' not found. Potential matches: {', '.join(matches[:3])}"
        
        nodes = nx.ancestors(self.lineage_graph, ds_id) if direction == "upstream" else nx.descendants(self.lineage_graph, ds_id)
        # Filter for other datasets or transformations
        return f"{direction.capitalize()} for {ds_name}: {', '.join(list(nodes)[:10])}"

    def blast_radius(self, path: str) -> str:
        """Trace downstream impact of a module or dataset."""
        if path not in self.module_graph and f"ds:{path}" not in self.lineage_graph:
            return "Node not found."
        
        target = path if path in self.module_graph else f"ds:{path}"
        graph = self.module_graph if path in self.module_graph else self.lineage_graph
        impact = nx.descendants(graph, target)
        return f"Impacted components: {', '.join(list(impact)[:15])}"

class Navigator:
    def __init__(self, repo_path: str, model: str = "gemini/gemini-2.0-flash"):
        self.repo_path = repo_path
        self.model = model
        
        # Check repo-local or root-local cartography
        local_dir = os.path.join(repo_path, ".cartography")
        root_dir = ".cartography" # Default from CLI analyze
        self.cartography_dir = local_dir if os.path.exists(local_dir) else root_dir
        
        if not os.path.exists(self.cartography_dir):
            raise FileNotFoundError(f"Analysis artifacts not found. Run 'analyze' first.")

        # Load graphs
        with open(os.path.join(self.cartography_dir, "module_graph.json"), "r") as f:
            m_data = json.load(f)
            self.module_graph = nx.node_link_graph(m_data["graph"])
            
        with open(os.path.join(self.cartography_dir, "lineage_graph.json"), "r") as f:
            l_data = json.load(f)
            self.lineage_graph = nx.node_link_graph(l_data["graph"])
            
        self.tools = NavigatorTools(self.module_graph, self.lineage_graph)

    async def ask(self, question: str) -> str:
        # Load CODEBASE.md for high-level context
        codebase_md = ""
        cb_path = os.path.join(self.cartography_dir, "CODEBASE.md")
        if os.path.exists(cb_path):
            with open(cb_path, "r") as f:
                codebase_md = f.read()

        # Context-building prompt
        context = f"""
        You are 'The Navigator', an expert guide for the codebase at {self.repo_path}.
        
        {codebase_md}
        
        The codebase has {len(self.module_graph.nodes)} structural nodes and {len(self.lineage_graph.nodes)} lineage nodes.
        
        Navigator Tools (Available Knowledge):
        - Module Graph: tracks imports, class hierarchies, and PageRank importance.
        - Lineage Graph: tracks data movement between files and tables.
        - Blast Radius: helper to find all components affected by a change.
        
        Question: {question}
        
        Please provide a detailed, expert answer based on the architecture summary above and the provided graph stats.
        If the question is about specific lineage, mention the source and target datasets.
        """
        
        response = await litellm.acompletion(
            model=self.model,
            messages=[{"role": "user", "content": context}],
            temperature=0.2
        )
        return response.choices[0].message.content
