import os
import argparse
import asyncio
from dotenv import load_dotenv
from src.orchestrator import Orchestrator

async def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="The Brownfield Cartographer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # Analyze subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Perform full codebase analysis")
    analyze_parser.add_argument("repo_path", help="Path to the repository to analyze")
    analyze_parser.add_argument("--output", default=".cartography", help="Directory to save artifacts")

    # Query subcommand
    query_parser = subparsers.add_parser("query", help="Query the codebase knowledge graph")
    query_parser.add_argument("repo_path", help="Path to the repository to query")
    query_parser.add_argument("question", help="Natural language question about the codebase")

    args = parser.parse_args()
    
    if args.command == "analyze":
        repo_path = args.repo_path
        
        # GitHub URL handling
        if repo_path.startswith(("http://", "https://")):
            print(f"Cloning repository: {repo_path}")
            target_dir = os.path.join("targets", repo_path.split("/")[-1].replace(".git", ""))
            os.makedirs("targets", exist_ok=True)
            if not os.path.exists(target_dir):
                from git import Repo
                Repo.clone_from(repo_path, target_dir)
            repo_path = target_dir

        if not os.path.exists(repo_path):
            print(f"Error: Repository path '{repo_path}' does not exist.")
            return

        orchestrator = Orchestrator(repo_path, args.output)
        await orchestrator.run()

    elif args.command == "query":
        from src.agents.navigator import Navigator
        
        repo_path = args.repo_path
        # Re-use the same model selection logic or a default
        llm_model = None
        if os.getenv("GROQ_API_KEY"):
            llm_model = "groq/llama-3.3-70b-versatile"
        elif os.getenv("GEMINI_API_KEY") and not os.getenv("GEMINI_API_KEY").startswith("your_"):
            llm_model = "gemini/gemini-2.0-flash"
            
        if not llm_model:
            print("Error: No LLM API key provided for querying.")
            return

        print(f"Querying Navigator for: {args.question}")
        navigator = Navigator(repo_path, model=llm_model)
        answer = await navigator.ask(args.question)
        print(f"\n--- NAVIGATOR ANSWER ---\n{answer}\n")

    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
