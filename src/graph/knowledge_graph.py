import networkx as nx
import json
from typing import Dict, List, Any, Optional

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, node_id: str, **kwargs):
        self.graph.add_node(node_id, **kwargs)

    def add_edge(self, source_id: str, target_id: str, **kwargs):
        self.graph.add_edge(source_id, target_id, **kwargs)

    def get_nodes(self) -> List[Dict[str, Any]]:
        return [{"id": n, **self.graph.nodes[n]} for n in self.graph.nodes]

    def get_edges(self) -> List[Dict[str, Any]]:
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({"source": u, "target": v, **data})
        return edges

    def serialize(self) -> Dict[str, Any]:
        return nx.node_link_data(self.graph)

    def find_sources(self, node_id: str) -> List[str]:
        if node_id not in self.graph:
            return []
        return list(nx.ancestors(self.graph, node_id))

    def find_sinks(self, node_id: str) -> List[str]:
        if node_id not in self.graph:
            return []
        return list(nx.descendants(self.graph, node_id))

    def blast_radius(self, node_id: str) -> int:
        if node_id not in self.graph:
            return 0
        return len(nx.descendants(self.graph, node_id))
