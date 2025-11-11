import os
from fastapi import APIRouter
from dotenv import load_dotenv
from supabase import create_client
import uuid

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

@router.get("/programmes/{programme_id}/knowledge-graph")
def get_knowledge_graph(programme_id: int):
    # Fetch programme data
    modules = supabase.table("modules").select("*").eq("programme_id", programme_id).execute().data or []
    skills = supabase.table("skills").select("*").eq("programme_id", programme_id).execute().data or []
    relations = supabase.table("skill_relations").select("*").eq("programme_id", programme_id).execute().data or []
    module_skills = supabase.table("module_skills").select("*").execute().data or []

    # Nodes
    nodes = []
    for m in modules:
        nodes.append({
            "id": f"module_{m['id']}",
            "label": m["title"],
            "type": "module"
        })
    for s in skills:
        nodes.append({
            "id": s["id"],
            "label": s["name"],
            "type": "skill",
            "category": s.get("category")
        })

    # Edges
    edges = []
    for ms in module_skills:
        edges.append({
            "source": f"module_{ms['module_id']}",
            "target": ms["skill_id"],
            "relation": "teaches"
        })
    for r in relations:
        edges.append({
            "source": r["source_skill_id"],
            "target": r["target_skill_id"],
            "relation": r.get("relation", "related")
        })

    return {"nodes": nodes, "edges": edges}

