import os
from typing import List, Dict, Any, Optional
import litellm
from src.models.node import ModuleNode

class Semanticist:
    def __init__(self, repo_path: str, model: str = "gemini/gemini-2.0-flash"):
        self.repo_path = repo_path
        self.model = model
        self.token_usage = 0
        self.cost = 0.0

    async def generate_purpose_statement(self, module_path: str, code_content: str) -> str:
        """Prompt LLM for a business-level purpose statement."""
        prompt = f"""
        Analyze the following code from the file '{module_path}'.
        Explain its primary business purpose and function in 2-3 sentences.
        Focus on WHAT it does for the system, not HOW it is implemented.
        Do NOT repeat the filename or docstrings if they are not helpful.
        
        CODE:
        {code_content[:4000]}  # Simple truncation for now
        """
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            self.token_usage += response.usage.total_tokens
            return response.choices[0].message.content.strip()
        except Exception as e:
            # print(f"Error calling LLM ({self.model}): {e}")
            return "Unable to determine purpose."

    async def answer_day_one_questions(self, context_summary: str) -> Dict[str, str]:
        """Synthesize the full architecture into Day-One answers."""
        prompt = f"""
        Based on the following architectural summary of the codebase, answer the Five FDE Day-One Questions:
        1. What is the primary data ingestion path?
        2. What are the 3-5 most critical output datasets/endpoints?
        3. What is the blast radius if the most critical module fails?
        4. Where is the business logic concentrated vs. distributed?
        5. What has changed most frequently in the last 90 days?

        Provide specific evidence (file paths and logic descriptions) for each.

        SUMMARY:
        {context_summary}
        """
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            self.token_usage += response.usage.total_tokens
            return response.choices[0].message.content.strip()
        except Exception as e:
            # print(f"Error calling LLM ({self.model}) for brief: {e}")
            return "Unable to generate brief."
