from fastapi import APIRouter, HTTPException
import os
import json
import httpx
import asyncio
from pydantic import BaseModel
from typing import List

# Initialize the router for all AI analysis endpoints
router = APIRouter(
    prefix="/degrees",
    tags=["analysis"],
    responses={404: {"description": "Not found"}},
)

# --- Pydantic Models for Data Structure (Unchanged) ---
class Node(BaseModel):
    id: int
    label: str
    group: str
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0

class Link(BaseModel):
    source: int
    target: int
    group: str

class Graph(BaseModel):
    nodes: List[Node]
    links: List[Link]

# --- Pydantic Models for New Specialized LLM Responses ---
class StrongSkillsResponse(BaseModel):
    """Response model for retrieving core competencies and summary."""
    strongest_skills: List[str]
    alignment_summary: str

class EnhancementResponse(BaseModel):
    """Response model for suggested courses/certs to enhance current skills."""
    enhancement_courses: List[str]

class ComplementarySkillsResponse(BaseModel):
    """Response model for future-proofing skills and job alignment."""
    complementary_skills: List[str]
    job_suggestions: List[str]

async def check_graph_data(degree_id: int) -> Graph:
    """Helper function to fetch graph data and handle 404 error if empty."""
    graph_data = await get_graph_data(degree_id)

    if not graph_data.nodes:
        raise HTTPException(
            status_code=404,
            detail=f"Degree with ID {degree_id} not found or no graph data available. Analysis aborted."
        )
    return graph_data


@router.get("/{degree_id}/strongest-skills", response_model=StrongSkillsResponse)
async def get_strong_skills_endpoint(degree_id: int):
    """
    1. Returns the best/strongest skills and overall career alignment summary
       based on the degree's knowledge graph.
    """
    graph_data = await check_graph_data(degree_id)
    analysis = await get_strongest_skills(graph_data)
    return analysis


@router.get("/{degree_id}/enhancement-courses", response_model=EnhancementResponse)
async def get_enhancement_endpoint(degree_id: int):
    """
    2. Uses AI to suggest external courses, certifications, or diplomas
       that enhance the current skill set.
    """
    graph_data = await check_graph_data(degree_id)
    analysis = await get_enhancement_suggestions(graph_data)
    return analysis


@router.get("/{degree_id}/complementary-skills", response_model=ComplementarySkillsResponse)
async def get_complementary_endpoint(degree_id: int):
    """
    3. Uses AI to suggest complementary skills for career future-proofing
       and recommends aligned job suggestions.
    """
    graph_data = await check_graph_data(degree_id)
    analysis = await get_complementary_skills(graph_data)
    return analysis

# --- Graph Data Retrieval (MOCK IMPLEMENTATION, Unchanged) ---
MOCK_DATABASE = {
    1: {
        "nodes": [
            {"id": 100, "label": "BSc Computer Science", "group": "Degree"},
            {"id": 201, "label": "Data Structures", "group": "Module"},
            {"id": 202, "label": "AI Fundamentals", "group": "Module"},
            {"id": 301, "label": "Python", "group": "Skill"},
            {"id": 302, "label": "Algorithms", "group": "Skill"},
            {"id": 303, "label": "Machine Learning", "group": "Skill"},
            {"id": 304, "label": "Graph Theory", "group": "Skill"},
        ],
        "links": [
            {"source": 100, "target": 201, "group": "degree-module"},
            {"source": 100, "target": 202, "group": "degree-module"},
            {"source": 201, "target": 301, "group": "module-skill"},
            {"source": 201, "target": 302, "group": "module-skill"},
            {"source": 202, "target": 303, "group": "module-skill"},
            {"source": 202, "target": 301, "group": "module-skill"},
            {"source": 201, "target": 304, "group": "module-skill"},
            {"source": 202, "target": 304, "group": "module-skill"},
        ]
    },
    2: {
        "nodes": [
            {"id": 101, "label": "BA Philosophy", "group": "Degree"},
            {"id": 203, "label": "Logic", "group": "Module"},
            {"id": 305, "label": "Critical Thinking", "group": "Skill"},
            {"id": 306, "label": "Ethics", "group": "Skill"},
        ],
        "links": [
            {"source": 101, "target": 203, "group": "degree-module"},
            {"source": 203, "target": 305, "group": "module-skill"},
            {"source": 203, "target": 306, "group": "module-skill"},
        ]
    }
}

async def get_graph_data(degree_id: int) -> Graph:
    """
    IMPLEMENTATION: Simulates an asynchronous query to a Supabase/PostgreSQL database.
    """
    print(f"INFO: Simulating async DB query for Degree ID {degree_id}...")
    await asyncio.sleep(0.1)
    raw_data = MOCK_DATABASE.get(degree_id)

    if not raw_data:
        print(f"WARNING: Graph data for Degree ID {degree_id} not found.")
        return Graph(nodes=[], links=[])

    try:
        nodes = [Node(**node_data) for node_data in raw_data['nodes']]
        links = [Link(**link_data) for link_data in raw_data['links']]
        return Graph(nodes=nodes, links=links)

    except Exception as e:
        print(f"ERROR: Failed to map raw data to Pydantic models: {e}")
        return Graph(nodes=[], links=[])

# --- Core LLM Analysis Utility ---
async def call_gemini_api(system_prompt: str, user_query: str, schema: dict) -> dict:
    """
    Generic utility function to handle the secure API call logic.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY environment variable is not set on the server."
        )

    apiUrl = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{apiUrl}?key={gemini_api_key}",
                headers={"Content-Type": "application/json"},
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            json_string = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")

            if not json_string:
                raise ValueError("Gemini API returned an empty analysis result.")

            return json.loads(json_string)

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error calling Gemini: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Gemini API call failed: {e.response.status_code}. Check key and usage limits."
        )
    except Exception as e:
        print(f"An unexpected error occurred during Gemini API call: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during analysis: {e}"
        )

# --- 1. Strongest Skills Service ---
async def get_strongest_skills(graph_data: Graph) -> StrongSkillsResponse:
    """Uses AI to identify and summarize the strongest skills."""
    system_prompt = "You are an expert curriculum analyst. Analyze the graph to identify core strengths based on skill centrality (Skills linked to many Modules are stronger). Provide a concise alignment summary."
    user_query = f"Analyze this knowledge graph. Identify the 5 strongest skills based on linkages and give a two-sentence career alignment summary. The raw graph data is:\n\n {json.dumps(graph_data.dict(), indent=2)}"

    schema = {
        "type": "OBJECT",
        "properties": {
            "strongest_skills": {
                "type": "ARRAY",
                "description": "List of the top 5 most central skills derived from the graph connections.",
                "items": {"type": "STRING"}
            },
            "alignment_summary": {
                "type": "STRING",
                "description": "A brief, two-sentence summary of the overall career alignment and focus."
            }
        }
    }

    analysis_data = await call_gemini_api(system_prompt, user_query, schema)
    return StrongSkillsResponse(**analysis_data)

# --- 2. Enhancement Courses Service ---
async def get_enhancement_suggestions(graph_data: Graph) -> EnhancementResponse:
    """Uses AI to suggest courses/certs to enhance the current skill set."""
    system_prompt = "You are an expert career advisor. Based on the student's current skill set (derived from the graph), recommend relevant and specific, high-value courses, certifications, or diplomas to substantially enhance those current skills."
    user_query = f"The student's current curriculum and skills are in this knowledge graph. Suggest 5 high-impact external courses or certifications (e.g., 'Google Professional ML Engineer Certification' or 'Coursera Deep Learning Specialization') that specifically build upon the established skills. The raw graph data is:\n\n {json.dumps(graph_data.dict(), indent=2)}"

    schema = {
        "type": "OBJECT",
        "properties": {
            "enhancement_courses": {
                "type": "ARRAY",
                "description": "List of 5 specific courses, certifications, or diplomas.",
                "items": {"type": "STRING"}
            }
        }
    }

    analysis_data = await call_gemini_api(system_prompt, user_query, schema)
    return EnhancementResponse(**analysis_data)

# --- 3. Complementary Skills Service ---
async def get_complementary_skills(graph_data: Graph) -> ComplementarySkillsResponse:
    """Uses AI to suggest complementary skills and future-proof career paths."""
    system_prompt = "You are a strategic career planner. Based on the provided skills, identify 5 emerging or complementary skills that are crucial for future-proofing a career in this domain. Also, recommend 3 relevant job titles."
    user_query = f"Analyze the current skills in this knowledge graph. Recommend 5 complementary skills needed to future-proof the career (e.g., communication, MLOps, DevOps) and suggest 3 aligned job roles. The raw graph data is:\n\n {json.dumps(graph_data.dict(), indent=2)}"

    schema = {
        "type": "OBJECT",
        "properties": {
            "complementary_skills": {
                "type": "ARRAY",
                "description": "List of 5 emerging or complementary skills for career longevity.",
                "items": {"type": "STRING"}
            },
            "job_suggestions": {
                "type": "ARRAY",
                "description": "List of 3 suitable future-aligned job titles.",
                "items": {"type": "STRING"}
            }
        }
    }

    analysis_data = await call_gemini_api(system_prompt, user_query, schema)
    return ComplementarySkillsResponse(**analysis_data)