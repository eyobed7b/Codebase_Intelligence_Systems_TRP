import os
import json
from typing import Dict, Any, List

class Archivist:
    def __init__(self, output_dir: str = ".cartography"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_codebase_md(self, surveyor_results: dict, hydrologist_results: dict, purpose_statements: dict):
        """Produce the CODEBASE.md artifact."""
        
        # Identify top modules by pagerank (complexity_score)
        nodes = surveyor_results.get("nodes", [])
        top_modules = sorted(
            [n for n in nodes if n["type"] == "module"], 
            key=lambda x: x.get("complexity_score", 0), 
            reverse=True
        )[:5]

        # Identify sources and sinks from lineage
        # This is a bit simplified for now
        lineage_nodes = hydrologist_results.get("nodes", [])
        
        content = "# CODEBASE.md - Persistent Project Context\n\n"
        content += "## 1. Architecture Overview\n"
        content += "This project implements a multi-language data engineering pipeline.\n\n"
        
        content += "## 2. Critical Path (Top Modules by PageRank)\n"
        for mod in top_modules:
            path = mod["path"]
            purpose = purpose_statements.get(path, "No purpose statement generated.")
            content += f"- **`{path}`**: {purpose}\n"
        
        content += "\n## 3. Data Sources & Sinks (Lineage Entry/Exit)\n"
        content += "The system processes local datasets into a relational database warehouse.\n\n"
        
        content += "## 4. Module Purpose Index\n"
        for mod in [n for n in nodes if n["type"] == "module"]:
            path = mod["path"]
            purpose = purpose_statements.get(path, mod.get("purpose_statement", "Module summary unavailable."))
            content += f"- **`{path}`**: {purpose}\n"
        
        file_path = os.path.join(self.output_dir, "CODEBASE.md")
        with open(file_path, "w") as f:
            f.write(content)
        
    def save_onboarding_brief(self, brief: str):
        file_path = os.path.join(self.output_dir, "onboarding_brief.md")
        with open(file_path, "w") as f:
            f.write(brief)

    def log_trace(self, action: str, details: dict):
        file_path = os.path.join(self.output_dir, "cartography_trace.jsonl")
        with open(file_path, "a") as f:
            f.write(json.dumps({"action": action, "details": details}) + "\n")
