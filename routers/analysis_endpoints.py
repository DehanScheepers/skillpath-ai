import os
import json
import httpx
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from supabase import Client
from database import get_supabase_client


# --- 1. Pydantic Models for Data Structure and Response ---

# Models for the rich skill data retrieved from the database (Ensures non-stale analysis)
class DetailedSkill(BaseModel):
    name: str
    category: str
    description: str


# Response Models for the three distinct API endpoints
class AlignmentSummaryResponse(BaseModel):
    alignment_summary: str = Field(...,
                                   description="A brief, three-sentence summary of the overall career alignment and focus.")
    strongest_skills: List[str] = Field(...,
                                        description="List of the top 5 most central skills derived from the curriculum.")


class DevelopmentSuggestionsResponse(BaseModel):
    enhancement_courses: List[str] = Field(...,
                                           description="List of 5 specific external courses, certifications, or diplomas.")
    complementary_skills: List[str] = Field(...,
                                            description="List of 5 emerging or complementary skills for career longevity.")


class JobSuggestionsResponse(BaseModel):
    job_suggestions: List[str] = Field(..., description="List of 3 suitable future-aligned job titles in South Africa.")


# --- 2. Core LLM Analysis Utility ---

async def call_gemini_api(system_prompt: str, user_query: str, schema: dict) -> dict:
    """
    Generic utility function to handle the secure API call logic with exponential backoff.
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

    # Retry logic with Exponential Backoff
    MAX_RETRIES = 3
    for i in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
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
            # Handle specific HTTP errors (4xx, 5xx)
            print(f"HTTP Error calling Gemini (Attempt {i + 1}): {e.response.text}")
            if i == MAX_RETRIES - 1:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Gemini API call failed after {MAX_RETRIES} attempts. Status: {e.response.status_code}"
                )
        except Exception as e:
            # Handle JSON parsing or other general errors
            print(f"An unexpected error occurred (Attempt {i + 1}): {e}")
            if i == MAX_RETRIES - 1:
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal server error during analysis after {MAX_RETRIES} attempts: {e}"
                )

        # Exponential backoff delay
        await asyncio.sleep(2 ** i)

    raise HTTPException(status_code=500, detail="Analysis failed due to unknown error after retries.")


# --- 3. Data Retrieval (Pre-analysis Step) ---

async def fetch_detailed_skills(degree_id: int, client: Client) -> List[DetailedSkill]:
    """
    Retrieves the full skill list (name, category, description) from Supabase.
    This rich data is crucial for preventing stale analysis suggestions.
    """
    try:
        # Fetch skill details (name, category, description) for the given degree
        skills_res = await client.table('extracted_skills') \
            .select('name, category, description') \
            .eq('degree_id', degree_id) \
            .execute()

        raw_skills = skills_res.data

        if not raw_skills:
            return []

        # Map raw data to Pydantic models for type safety
        return [DetailedSkill(**skill) for skill in raw_skills]

    except Exception as e:
        print(f"Supabase Read Error during detailed skill fetch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve skill data for analysis: {e}")


# --- 4. LLM Analysis Service Functions (3 Separate Calls) ---

def _format_skills_for_prompt(detailed_skills: List[DetailedSkill]) -> str:
    """Helper to format the detailed skill data for the LLM prompt."""
    return '\n'.join([
        f"Skill: {s.name} | Category: {s.category} | Description: {s.description}"
        for s in detailed_skills
    ])


# Service 1: Alignment Summary and Strongest Skills
async def get_alignment_summary(detailed_skills: List[DetailedSkill]) -> Dict[str, Any]:
    system_prompt = "You are an expert career analyst. Analyze the comprehensive skill set to determine the core alignment and identify the central skills of the curriculum."
    user_query = f"""
    Based on the following {len(detailed_skills)} detailed skills:
    {_format_skills_for_prompt(detailed_skills)}

    1. Write a 3-sentence 'alignment summary' of the overall career focus of the degree.
    2. Identify the top 5 'strongest skills' (skills central to the whole curriculum).
    """

    schema = AlignmentSummaryResponse.model_json_schema()
    return await call_gemini_api(system_prompt, user_query, schema)


# Service 2: Development and Enhancement Suggestions
async def get_development_suggestions(detailed_skills: List[DetailedSkill]) -> Dict[str, Any]:
    system_prompt = "You are an expert strategic planner. Analyze the provided skill set to suggest specific enhancement opportunities and future-proofing skills."
    user_query = f"""
    Based on the following {len(detailed_skills)} detailed skills:
    {_format_skills_for_prompt(detailed_skills)}

    1. Suggest 5 'enhancement courses' (specific, external courses, certifications, or diplomas to build on the existing skills).
    2. Recommend 5 'complementary skills' (emerging skills like MLOps, specific soft skills, or domain knowledge needed to future-proof the career).
    """

    schema = DevelopmentSuggestionsResponse.model_json_schema()
    return await call_gemini_api(system_prompt, user_query, schema)


# Service 3: Job Suggestions
async def get_job_suggestions(detailed_skills: List[DetailedSkill]) -> Dict[str, Any]:
    system_prompt = "You are an expert recruitment specialist focused on the South African market. Analyze the skill set to provide relevant job titles."
    user_query = f"""
    Based on the following {len(detailed_skills)} detailed skills:
    {_format_skills_for_prompt(detailed_skills)}

    Suggest 3 'job suggestions' (suitable future-aligned job titles specifically in the South African (SA) market context).
    """

    schema = JobSuggestionsResponse.model_json_schema()
    return await call_gemini_api(system_prompt, user_query, schema)


# --- 5. FastAPI Router and Endpoints (3 Separate Endpoints Restored) ---

router = APIRouter(
    prefix="/api/degrees",
    tags=["analysis_core"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{degree_id}/summary", response_model=AlignmentSummaryResponse)
async def get_alignment_summary_endpoint(
        degree_id: int,
        client: Client = Depends(get_supabase_client)
):
    """Retrieves the Alignment Summary and Strongest Skills (API 1 of 3)."""
    detailed_skills_data = await fetch_detailed_skills(degree_id, client)

    if not detailed_skills_data:
        raise HTTPException(
            status_code=404,
            detail=f"No skills found for Degree ID {degree_id}. Analysis aborted."
        )

    analysis_data = await get_alignment_summary(detailed_skills_data)
    return AlignmentSummaryResponse(**analysis_data)


@router.get("/{degree_id}/development", response_model=DevelopmentSuggestionsResponse)
async def get_development_suggestions_endpoint(
        degree_id: int,
        client: Client = Depends(get_supabase_client)
):
    """Retrieves Enhancement and Complementary Skill Suggestions (API 2 of 3)."""
    detailed_skills_data = await fetch_detailed_skills(degree_id, client)

    if not detailed_skills_data:
        raise HTTPException(
            status_code=404,
            detail=f"No skills found for Degree ID {degree_id}. Analysis aborted."
        )

    analysis_data = await get_development_suggestions(detailed_skills_data)
    return DevelopmentSuggestionsResponse(**analysis_data)


@router.get("/{degree_id}/jobs", response_model=JobSuggestionsResponse)
async def get_job_suggestions_endpoint(
        degree_id: int,
        client: Client = Depends(get_supabase_client)
):
    """Retrieves relevant Job Suggestions (API 3 of 3)."""
    detailed_skills_data = await fetch_detailed_skills(degree_id, client)

    if not detailed_skills_data:
        raise HTTPException(
            status_code=404,
            detail=f"No skills found for Degree ID {degree_id}. Analysis aborted."
        )

    analysis_data = await get_job_suggestions(detailed_skills_data)
    return JobSuggestionsResponse(**analysis_data)