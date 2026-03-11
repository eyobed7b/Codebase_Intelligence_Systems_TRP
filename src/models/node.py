from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field

class StorageType(str, Enum):
    TABLE = "table"
    FILE = "file"
    STREAM = "stream"
    API = "api"

class NodeBase(BaseModel):
    id: str  # Unique identifier (e.g. file path or table name)
    type: str

class ModuleNode(NodeBase):
    path: str
    language: str
    purpose_statement: Optional[str] = None
    domain_cluster: Optional[str] = None
    complexity_score: float = 0.0
    change_velocity_30d: float = 0.0
    is_dead_code_candidate: bool = False
    last_modified: Optional[str] = None
    functions: List[str] = Field(default_factory=list)
    classes: List[Dict[str, Any]] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)
    type: str = "module"

class DatasetNode(NodeBase):
    name: str
    storage_type: StorageType
    schema_snapshot: Optional[Dict[str, str]] = None
    freshness_sla: Optional[str] = None
    owner: Optional[str] = None
    is_source_of_truth: bool = False
    type: str = "dataset"

class FunctionNode(NodeBase):
    qualified_name: str
    parent_module: str
    signature: str
    purpose_statement: Optional[str] = None
    call_count_within_repo: int = 0
    is_public_api: bool = False
    type: str = "function"

class TransformationNode(NodeBase):
    source_datasets: List[str]
    target_datasets: List[str]
    transformation_type: str
    source_file: str
    line_range: Tuple[int, int]
    sql_query_if_applicable: Optional[str] = None
    type: str = "transformation"
