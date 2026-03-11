import sqlglot
from sqlglot.optimizer.qualify import qualify
from sqlglot import exp, parse_one
from typing import List, Set, Dict, Any, Optional

class SQLLineageAnalyzer:
    def __init__(self, dialect: str = "postgres"):
        self.dialect = dialect

    def extract_lineage(self, sql_content: str) -> Dict[str, Any]:
        """Extract table dependencies from a SQL query."""
        try:
            # First, parse the SQL
            expressions = sqlglot.parse(sql_content, read=self.dialect)
            
            # Collect all inputs (FROM, JOIN) and outputs (CREATE TABLE, INSERT INTO)
            sources = set()
            targets = set()
            
            for expression in expressions:
                # treat UPDATE/DELETE as both source and target
                if isinstance(expression, (exp.Update, exp.Delete)):
                    tbl = expression.this
                    if tbl:
                        sources.add(tbl.sql())
                        targets.add(tbl.sql())

                # Check for CREATE TABLE or INSERT
                if isinstance(expression, (exp.Create, exp.Insert)):
                    # expression.this is usually the table being created/inserted
                    tbl = expression.this
                    if isinstance(tbl, exp.Table):
                        targets.add(tbl.sql())

                # generic table references: default to source unless we already
                # classified them as a target above
                for table in expression.find_all(exp.Table):
                    name = table.sql()
                    if name in targets:
                        continue
                    # if parent is a Create/Insert/Update/Delete treat as target
                    parent = table.parent
                    if isinstance(parent, (exp.Create, exp.Insert, exp.Update, exp.Delete)):
                        targets.add(name)
                    else:
                        sources.add(name)

                # Find all sources in FROM and JOIN (redundant but safe)
                for from_clause in expression.find_all(exp.From):
                    for table in from_clause.find_all(exp.Table):
                        sources.add(table.sql())

                for join_clause in expression.find_all(exp.Join):
                    for table in join_clause.find_all(exp.Table):
                        sources.add(table.sql())

                # CTEs may reference other tables; pull them too
                for cte in expression.find_all(exp.CTE):
                    for table in cte.find_all(exp.Table):
                        sources.add(table.sql())
            
            # Simple lineage logic: if no target found, it's just a SELECT?
            # For dbt, we'd need to handle ref() calls.
            
            return {
                "sources": list(sources),
                "targets": list(targets),
                "sql": sql_content
            }
        except Exception as e:
            # print(f"Error parsing SQL: {e}")
            return {"sources": [], "targets": [], "error": str(e)}

    def analyze_dbt_model(self, model_content: str) -> Dict[str, Any]:
        """Specific logic for dbt models (handling jinja ref macros)."""
        # For now, let's keep it simple and just look for ref('table')
        import re
        refs = re.findall(r"ref\(['\"](.+?)['\"]\)", model_content)
        
        # Also try to parse the SQL (might need to strip jinja first)
        sql_stripped = re.sub(r"\{\{.*?\}\}", "", model_content)
        lineage = self.extract_lineage(sql_stripped)
        
        lineage["sources"].extend(refs)
        return lineage
