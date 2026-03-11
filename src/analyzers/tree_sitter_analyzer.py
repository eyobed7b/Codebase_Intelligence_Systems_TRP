import os
from typing import Dict, List, Optional, Any, Set
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_python as tspython

class LanguageRouter:
    def __init__(self):
        self.languages = {
            ".py": Language(tspython.language()),
            # Add other languages as needed
        }
        self.parsers = {ext: Parser(lang) for ext, lang in self.languages.items()}

    def get_parser(self, file_path: str) -> Optional[Parser]:
        _, ext = os.path.splitext(file_path)
        return self.parsers.get(ext)

    def get_language(self, file_path: str) -> Optional[Language]:
        _, ext = os.path.splitext(file_path)
        return self.languages.get(ext)

class TreeSitterAnalyzer:
    def __init__(self):
        self.router = LanguageRouter()

    def parse_file(self, file_path: str) -> Optional[Any]:
        parser = self.router.get_parser(file_path)
        if not parser:
            return None
        
        with open(file_path, "rb") as f:
            content = f.read()
            tree = parser.parse(content)
            return tree

    def extract_imports(self, file_path: str, tree: Any) -> List[str]:
        # Implementation for Python imports
        if not file_path.endswith(".py"):
            return []
            
        imports = []
        root_node = tree.root_node
        
        # Simple query for Python imports
        query_text = """
        (import_statement (dotted_name) @import)
        (import_from_statement (dotted_name) @module)
        """
        language = self.router.get_language(file_path)
        query = language.query(query_text)
        cursor = QueryCursor(query)
        captures_dict = cursor.captures(root_node)
        
        with open(file_path, "rb") as f:
            content = f.read()
            for name, nodes in captures_dict.items():
                if name in ["import", "module"]:
                    for node in nodes:
                        imports.append(content[node.start_byte:node.end_byte].decode("utf-8"))
                    
        return imports

    def extract_functions(self, file_path: str, tree: Any) -> List[Dict[str, Any]]:
        # Implementation for Python functions
        if not file_path.endswith(".py"):
            return []
            
        functions = []
        root_node = tree.root_node
        
        query_text = """
        (function_definition
          name: (identifier) @name
          parameters: (parameters) @params) @func
        """
        language = self.router.get_language(file_path)
        query = language.query(query_text)
        cursor = QueryCursor(query)
        captures_dict = cursor.captures(root_node)
        
        # In this new API, we get lists of nodes per capture name.
        # But we need to correlate @name and @params to the same @func.
        # This is harder with the dict return.
        
        # Let's try QueryCursor.matches(node) instead.
        # matches returns a list of pattern matches.
        
        matches = cursor.matches(root_node)
        # matches: list of (pattern_index, captures_dict)
        
        with open(file_path, "rb") as f:
            content = f.read()
            for pattern_index, captures in matches:
                # patterns: 0 is our function_definition
                func_node = captures.get("func", [None])[0]
                name_node = captures.get("name", [None])[0]
                params_node = captures.get("params", [None])[0]
                
                if name_node and func_node:
                    name_id = content[name_node.start_byte:name_node.end_byte].decode("utf-8")
                    params_id = content[params_node.start_byte:params_node.end_byte].decode("utf-8") if params_node else "()"
                    functions.append({
                        "name": name_id,
                        "signature": f"{name_id}{params_id}",
                        "line_range": (func_node.start_point[0] + 1, func_node.end_point[0] + 1)
                    })
        
        return functions
    def extract_classes(self, file_path: str, tree: Any) -> List[Dict[str, Any]]:
        # Implementation for Python classes
        if not file_path.endswith(".py"):
            return []
            
        classes = []
        root_node = tree.root_node
        
        query_text = """
        (class_definition
          name: (identifier) @name
          superclasses: (argument_list) @supers
        ) @class
        (class_definition
          name: (identifier) @name
          !superclasses
        ) @class_no_supers
        """
        language = self.router.get_language(file_path)
        query = language.query(query_text)
        cursor = QueryCursor(query)
        matches = cursor.matches(root_node)
        
        with open(file_path, "rb") as f:
            content = f.read()
            for pattern_index, captures in matches:
                name_node = captures.get("name", [None])[0]
                supers_node = captures.get("supers", [None])[0]
                
                if name_node:
                    name_id = content[name_node.start_byte:name_node.end_byte].decode("utf-8")
                    bases = []
                    if supers_node:
                        # Extract all identifiers from the argument list
                        for child in supers_node.children:
                            if child.type == "identifier":
                                bases.append(content[child.start_byte:child.end_byte].decode("utf-8"))
                    
                    classes.append({
                        "name": name_id,
                        "inheritance": bases
                    })
        
        return classes
