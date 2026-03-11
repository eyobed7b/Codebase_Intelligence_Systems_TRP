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
        # Interactive query mode or single question
        print(f"Querying: {args.question}")
        # To be implemented: Navigator interaction
        print("Navigator query interface in interactive mode not fully implemented yet.")
        print(f"Suggesting: Trace lineage for '{args.question}'")

    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
