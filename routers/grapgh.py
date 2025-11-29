from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from database import get_supabase_client
from typing import Dict, List, Any

# Change the prefix slightly to prepare for the new route structure
router = APIRouter(prefix="/api", tags=["Graph Visualization"])


@router.get("/degrees/{degree_id}/graph", response_model=Dict[str, List[Dict[str, Any]]])
async def get_degree_graph(
        degree_id: int,  # Capture the degree ID from the path
        client: Client = Depends(get_supabase_client)
):
    """
    Fetches Degrees, Modules, and Skills for a specific degree_id and formats them
    as a JSON Graph (Nodes & Links) for the frontend visualization library.

    Structure: Degree -> Module -> Skill

    Data Schema used:
    - Nodes: { id, label, group, val, [category] }
    - Links: { source, target, [group] }
    """
    try:
        # 1. Fetch Degrees (Top-level Nodes) - FILTERED BY ID
        # Since we only expect one degree, we use .eq('id', degree_id) and .single()
        degree_res = await client.table('degrees').select('id, name').eq('id', degree_id).single().execute()
        degree = degree_res.data
        # Put the single result into a list for consistent processing below
        degrees = [degree]

        # 2. Fetch Modules (Mid-level Nodes) - FILTERED BY degree_id
        modules_res = await client.table('modules').select('id, name, degree_id').eq('degree_id', degree_id).execute()
        modules = modules_res.data

        # 3. Fetch Skills (Low-level Nodes & Module -> Skill Edges) - FILTERED BY degree_id
        # Crucially, we must filter extracted_skills by degree_id
        skills_res = await client.table('extracted_skills').select('name, category, module_id').eq('degree_id',
                                                                                                   degree_id).execute()
        skills = skills_res.data

    except Exception as e:
        # Handle the common Supabase error if the single item is not found (404)
        if "PostgrestError" in str(e) and "rows not found" in str(e):
            raise HTTPException(status_code=404, detail=f"Degree with ID {degree_id} not found.")

        print(f"Graph Data Fetch Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch graph data from Supabase: {e}")

    # --- Build the Graph Structure ---
    nodes = []
    links = []

    added_node_ids = set()

    # A. Process Degrees (Group: "Degree") - Only one degree now
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
        # Since we only fetched modules belonging to this degree, we use its degree_id
        deg_id = f"deg_{mod['degree_id']}"

        # 1. Add Module Node if not already added
        if mod_id not in added_node_ids:
            nodes.append({
                "id": mod_id,
                "label": mod['name'],
                "group": "Module",
                "val": 20
            })
            added_node_ids.add(mod_id)

        # 2. Add Link (Edge) from Degree -> Module
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

        # 1. Add Skill Node if not already added
        if skill_id not in added_node_ids:
            nodes.append({
                "id": skill_id,
                "label": skill['name'],
                "group": "Skill",
                "category": skill.get('category', 'Generic'),
                "val": 10
            })
            added_node_ids.add(skill_id)

        # 2. Add Link (Edge) from Module -> Skill
        links.append({
            "source": mod_id,
            "target": skill_id,
            "group": "module-skill"
        })

    return {
        "nodes": nodes,
        "links": links
    }