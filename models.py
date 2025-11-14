from pydantic import BaseModel
from typing import List, Optional

class Programme(BaseModel):
    id: int
    name: str
    description: Optional[str]

class Module(BaseModel):
    id: int
    programme_id: int
    code: str
    name: str
    year_level: Optional[int]
    description: Optional[str]

class Skill(BaseModel):
    id: str
    programme_id: int
    module_id: int
    name: str
    category: Optional[str]
    description: Optional[str]

class Relation(BaseModel):
    source_skill_id: str
    target_skill_id: str
    relation: str
    confidence: float = 0.8