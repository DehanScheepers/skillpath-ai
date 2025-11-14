from fastapi import APIRouter
from database import connect

router = APIRouter(prefix="/api/graph")

@router.get("/programme/{programme_id}/knowledge-graph")
async def get_graph(programme_id: int):
    conn = await connect()

    modules = await conn.fetch(
        "SELECT id, name FROM modules WHERE programme_id=$1", programme_id
    )
    skills = await conn.fetch(
        "SELECT id, name FROM skills WHERE programme_id=$1", programme_id
    )
    relations = await conn.fetch(
        "SELECT source_skill_id, target_skill_id, relation FROM skill_relations WHERE programme_id=$1",
        programme_id
    )

    nodes = []
    edges = []

    for m in modules:
        nodes.append({ "id": str(m["id"]), "name": m["name"], "type": "module" })

    for s in skills:
        nodes.append({ "id": s["id"], "name": s["name"], "type": "skill" })

    module_skill_links = await conn.fetch("""
        SELECT module_id, skill_id FROM module_skills
        JOIN modules ON module_skills.module_id = modules.id
        WHERE programme_id=$1
    """, programme_id)

    for link in module_skill_links:
        edges.append({ "source": str(link["module_id"]), "target": link["skill_id"], "type": "module-skill" })

    for r in relations:
        edges.append({
            "source": r["source_skill_id"],
            "target": r["target_skill_id"],
            "type": r["relation"]
        })

    return { "nodes": nodes, "edges": edges }
