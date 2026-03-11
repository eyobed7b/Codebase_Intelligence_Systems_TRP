import yaml
import json
import os
from typing import List, Dict, Any, Optional

class DAGConfigParser:
    """Parses Airflow DAGs, dbt models, and other YAML/JSON configurations."""
    
    def parse_yaml(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            return None

    def parse_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def extract_sql_fragments(self, config: Any) -> List[str]:
        fragments = []
        
        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    kl = k.lower()
                    if kl in ("sql", "query") and isinstance(v, str):
                        fragments.append(v)
                    else:
                        walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
        
        walk(config)
        return fragments

    def extract_dataset_names(self, config: Any) -> List[str]:
        names = []
        
        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    kl = k.lower()
                    if kl == "name" and isinstance(v, str):
                        names.append(v)
                    else:
                        walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
                    
        walk(config)
        return names
