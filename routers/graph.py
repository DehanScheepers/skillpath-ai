from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from database import get_supabase_client
from typing import List, Dict, Any

router = APIRouter(prefix="/api", tags=["Knowledge Graph"])

# Define the structure for the resulting graph data for better clarity
GraphResponse = Dict[str, List[Dict[str, Any]]]


@router.get("/programmes/{programme_id}/knowledge-graph", response_model=GraphResponse)
async def get_knowledge_graph(
        programme_id: int,
        # Inject the asynchronous Supabase client object
        client: Client = Depends(get_supabase_client)
):
    # --- Helper function to fetch data from Supabase ---
    async def fetch_data(table_name: str, columns: str):
        """Fetches data for a specific programme from a given table."""
        try:
            # Use the asynchronous Supabase client query methods
            result = await client.table(table_name) \
                .select(columns) \
                .eq('programme_id', programme_id) \
                .execute()
            return result.data
        except Exception as e:
            print(f"Supabase fetch error for table {table_name}: {e}")
            # Raise an HTTPException if the database connection or query fails
            raise HTTPException(status_code=500, detail=f"Failed to fetch data from {table_name}: {e}")

    # -----------------------------
    # 1. Fetch Modules (Nodes)
    # -----------------------------
    modules_data = await fetch_data("modules", "id, name")

    # -----------------------------
    # 2. Fetch Skills (Nodes) and Module -> Skill Edges
    # We fetch skills (extracted_skills) and get the module_id directly from the same table
    # -----------------------------
    skills_and_edges_data = await fetch_data("extracted_skills", "id, name, module_id")

    # -----------------------------
    # 3. Fetch Skill → Skill edges
    # -----------------------------
    skill_relations_data = await fetch_data("skill_relations", "source_skill_id, target_skill_id, relation, confidence")

    # -----------------------------
    # 4. Build Final Graph Response
    # -----------------------------
    nodes = []
    edges = []

    # MODULE NODES
    for m in modules_data:
        nodes.append({
            "id": str(m["id"]),
            "name": m["name"],
            "type": "module"
        })

    # SKILL NODES and MODULE → SKILL EDGES (built from the same dataset)
    for s in skills_and_edges_data:
        # SKILL NODES
        nodes.append({
            "id": str(s["id"]),
            "name": s["name"],
            "type": "skill"
        })

        # MODULE → SKILL EDGES
        edges.append({
            "source": str(s["module_id"]),
            "target": str(s["id"]),
            "type": "module-skill"
        })

    # SKILL → SKILL RELATION EDGES
    for rel in skill_relations_data:
        edges.append({
            "source": str(rel["source_skill_id"]),
            "target": str(rel["target_skill_id"]),
            "type": rel["relation"],
            "confidence": float(rel["confidence"])
        })

    # -----------------------------
    # 5. Return Final JSON
    # -----------------------------
    return {
        "nodes": nodes,
        "edges": edges
    }