from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from database import get_supabase_client
from typing import Dict, List, Any
import json

router = APIRouter(prefix="/api", tags=["Graph Visualization"])

def _build_graph_json(degrees, modules, skills) -> Dict[str, List[Dict[str, Any]]]:
    """
    Internal function to build the Nodes and Links structure from database query results.
    This logic is extracted from the original GET endpoint.
    """
    nodes = []
    links = []
    added_node_ids = set()

    # A. Process Degrees (Group: "Degree") - Assumes degrees is a list with one item
    for deg in degrees:
        deg_id = f"deg_{deg['id']}"
        if deg_id not in added_node_ids:
            nodes.append({
                "id": deg_id,
                "label": deg['name'],
                "group": "Degree",
                "val": 30
            })
            added_node_ids.add(deg_id)

    # B. Process Modules (Group: "Module") and Degree -> Module Links
    for mod in modules:
        mod_id = f"mod_{mod['id']}"
        deg_id = f"deg_{mod['degree_id']}"

        if mod_id not in added_node_ids:
            nodes.append({
                "id": mod_id,
                "label": mod['name'],
                "group": "Module",
                "val": 20
            })
            added_node_ids.add(mod_id)

        links.append({
            "source": deg_id,
            "target": mod_id,
            "group": "degree-module"
        })

    # C. Process Skills (Group: "Skill") and Module -> Skill Links
    for skill in skills:
        # Use skill name as ID, also prefixed
        skill_id = f"skill_{skill['name'].replace(' ', '_').lower()}"
        mod_id = f"mod_{skill['module_id']}"

        if skill_id not in added_node_ids:
            nodes.append({
                "id": skill_id,
                "label": skill['name'],
                "group": "Skill",
                "category": skill.get('category', 'Generic'),
                "val": 10
            })
            added_node_ids.add(skill_id)

        links.append({
            "source": mod_id,
            "target": skill_id,
            "group": "module-skill"
        })

    return {
        "nodes": nodes,
        "links": links
    }


# --- NEW POST ENDPOINT: Calculates and SAVES the graph ---
@router.post("/degrees/{degree_id}/process-graph", status_code=status.HTTP_201_CREATED)
async def process_and_save_graph(
        degree_id: int,
        client: Client = Depends(get_supabase_client)
):
    """
    Calculates the full graph structure for a degree from its raw components
    (Modules, Skills) and persists the resulting JSON into the degree_graphs table.
    """
    try:
        # 1. Fetch raw data
        degree_res = await client.table('degrees').select('id, name').eq('id', degree_id).single().execute()
        degree = degree_res.data
        degrees = [degree]

        modules_res = await client.table('modules').select('id, name, degree_id').eq('degree_id', degree_id).execute()
        modules = modules_res.data

        skills_res = await client.table('extracted_skills').select('name, category, module_id').eq('degree_id',
                                                                                                   degree_id).execute()
        skills = skills_res.data

    except Exception as e:
        if "PostgrestError" in str(e) and "rows not found" in str(e):
            raise HTTPException(status_code=404, detail=f"Degree with ID {degree_id} not found.")

        print(f"Graph Data Fetch Error during processing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch raw graph data from Supabase: {e}")

    # 2. Build the graph structure using the internal function
    graph_data = _build_graph_json(degrees, modules, skills)

    # 3. Save the JSON to the new table (Upsert logic to handle updates)
    try:
        await client.table('degree_graphs').upsert(
            {
                "degree_id": degree_id,
                "graph_json": graph_data
            },
            on_conflict='degree_id'
        ).execute()

    except Exception as e:
        print(f"Supabase Write Error (degree_graphs): {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save processed graph data: {e}")

    return {
        "message": f"Graph for Degree ID {degree_id} processed and saved successfully.",
        "nodes_count": len(graph_data['nodes'])
    }


# --- UPDATED GET ENDPOINT: Retrieves the SAVED graph JSON ---
@router.get("/degrees/{degree_id}/graph", response_model=Dict[str, List[Dict[str, Any]]])
async def get_degree_graph(
        degree_id: int,  # Capture the degree ID from the path
        client: Client = Depends(get_supabase_client)
):
    """
    Retrieves the pre-calculated knowledge graph structure (Nodes & Links)
    from the 'degree_graphs' table.
    """
    try:
        # Fetch the stored JSON object directly
        graph_res = await client.table('degree_graphs') \
            .select('graph_json') \
            .eq('degree_id', degree_id) \
            .single() \
            .execute()

        # The result data contains the graph_json field
        graph_data = graph_res.data

        # Return the actual JSON content stored in the graph_json column
        return graph_data['graph_json']

    except Exception as e:
        # Handle the common Supabase error if the single item is not found (404)
        if "PostgrestError" in str(e) and "rows not found" in str(e):
            raise HTTPException(status_code=404,
                                detail=f"Graph for Degree ID {degree_id} not found. Please run the POST /process-graph endpoint first.")

        print(f"Graph Retrieval Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stored graph data: {e}")