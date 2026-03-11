import os
import json
import networkx as nx
import asyncio
from src.agents.surveyor import Surveyor
from src.agents.hydrologist import Hydrologist
from src.agents.semanticist import Semanticist
from src.agents.archivist import Archivist

class Orchestrator:
    def __init__(self, repo_path: str, output_dir: str = ".cartography"):
        self.repo_path = repo_path
        self.output_dir = output_dir
        self.archivist = Archivist(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    async def run(self):
        """Run the full Cartographer pipeline: Surveyor -> Hydrologist -> Semanticist -> Archivist."""
        print(f"Starting full analysis of: {self.repo_path}")
        
        # 1. Surveyor phase (Static Structure)
        surveyor = Surveyor(self.repo_path)
        surveyor.analyze()
        surveyor_results = surveyor.get_results()
        self.archivist.log_trace("SURVEYOR_COMPLETE", {"nodes_count": len(surveyor_results["nodes"])})

        # 2. Hydrologist phase (Data Lineage)
        hydrologist = Hydrologist(self.repo_path)
        hydrologist.analyze()
        hydrologist_results = hydrologist.get_results()
        self.archivist.log_trace("HYDROLOGIST_COMPLETE", {"nodes_count": len(hydrologist_results["nodes"])})

        # 3. Semanticist phase (LLM-Powered Analysis) - Optional based on API key
        purpose_statements = {}
        
        # Decide which LLM to use
        llm_model = None
        if os.getenv("GROQ_API_KEY"):
            llm_model = "groq/llama-3.3-70b-versatile"
        elif os.getenv("GEMINI_API_KEY") and not os.getenv("GEMINI_API_KEY").startswith("your_"):
            llm_model = "gemini/gemini-2.0-flash"
        elif os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY").startswith("your_"):
            llm_model = "openai/gpt-4o-mini"

        if llm_model:
            print(f"Running Semanticist analysis using {llm_model}...")
            semanticist = Semanticist(self.repo_path, model=llm_model)
            
            # For each module, generate a purpose statement
            for mod in [n for n in surveyor_results["nodes"] if n["type"] == "module"]:
                path = mod["path"]
                full_path = os.path.join(self.repo_path, path)
                try:
                    with open(full_path, "r") as f:
                        code = f.read()
                        purpose = await semanticist.generate_purpose_statement(path, code)
                        purpose_statements[path] = purpose
                except:
                    purpose_statements[path] = "Error reading module."
            
            # Answer Day-One Questions
            context_summary = f"Modules: {list(purpose_statements.keys())}\nLineage: {hydrologist_results['graph']['edges']}"
            brief = await semanticist.answer_day_one_questions(context_summary)
            self.archivist.save_onboarding_brief(brief)
            self.archivist.log_trace("SEMANTICIST_COMPLETE", {"token_usage": semanticist.token_usage, "model": llm_model})
        else:
            print("Skipping Semanticist (No valid API key found for Groq, Gemini, or OpenAI).")
            # Use basic summaries if LLM skipped
            for mod in [n for n in surveyor_results["nodes"] if n["type"] == "module"]:
                purpose_statements[mod["path"]] = "LLM purpose extraction skipped."

        # 4. Archivist phase (Deliverables)
        self.archivist.generate_codebase_md(surveyor_results, hydrologist_results, purpose_statements)
        self._save_to_json(surveyor_results, "module_graph.json")
        self._save_to_json(hydrologist_results, "lineage_graph.json")
        self.archivist.log_trace("ARCHIVIST_COMPLETE", {"artifacts": [".cartography/CODEBASE.md", ".cartography/module_graph.json"]})
        
        print(f"Analysis complete. Results saved in: {self.output_dir}")

    def _save_to_json(self, results: dict, filename: str):
        file_path = os.path.join(self.output_dir, filename)
        with open(file_path, "w") as f:
            json.dump(results, f, indent=2)
