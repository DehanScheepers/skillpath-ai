from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedSkill(BaseModel):
    """Schema for a single skill extracted by Gemini."""
    skill_name: str = Field(..., description="The standardized name of the skill.")
    skill_category: str = Field(..., description="e.g., 'Technical', 'Soft', 'Domain'.")
    ai_confidence: float = Field(..., ge=0.6, le=1.0, description="AI's confidence score (0.0 to 1.0).")

class GeminiSkillsResponse(BaseModel):
    """The full JSON schema expected from Gemini for a module."""
    module_code: str
    extracted_skills: List[ExtractedSkill]

class SkillNode(BaseModel):
    """Represents a Skill node for the Bubble Diagram."""
    id: str  # Use the skill name or a unique ID for the graph
    name: str
    category: str
    is_core: bool = Field(False, description="True if this is one of the user's current skills.")
    is_suggested: bool = Field(False, description="True if this is a newly suggested skill.")

class SkillRelationship(BaseModel):
    """Represents an edge/connection for the Bubble Diagram."""
    source: str  # ID of the source skill
    target: str  # ID of the target skill
    strength: float = Field(..., description="The strength/weight of the connection.")

class BubbleDiagramData(BaseModel):
    """The complete payload for the frontend visualization."""
    nodes: List[SkillNode]
    links: List[SkillRelationship]

class Degree(BaseModel):
    """For listing available degrees."""
    id: int
    name: str
    level: str