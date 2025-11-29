from fastapi import APIRouter, HTTPException
from analysis_service import (
    Graph,
    StrongSkillsResponse,
    EnhancementResponse,
    ComplementarySkillsResponse,
    get_graph_data,
    get_strongest_skills,
    get_enhancement_suggestions,
    get_complementary_skills
)

# Initialize the router for all AI analysis endpoints
router = APIRouter(
    prefix="/degrees",
    tags=["analysis"],
    responses={404: {"description": "Not found"}},
)


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