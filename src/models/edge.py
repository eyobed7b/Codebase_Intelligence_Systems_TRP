from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel

class EdgeType(str, Enum):
    IMPORTS = "IMPORTS"
    PRODUCES = "PRODUCES"
    CONSUMES = "CONSUMES"
    CALLS = "CALLS"
    CONFIGURES = "CONFIGURES"

class EdgeBase(BaseModel):
    source: str
    target: str
    type: EdgeType
    metadata: Dict[str, Any] = {}
