from fastapi import APIRouter
from database import connect

router = APIRouter(prefix="/api")

@router.get("/programmes/{programme_id}/knowledge-graph")
async def get_knowledge_graph(programme_id: int):
    conn = await connect()

    # -----------------------------
    # 1. Fetch Modules
    # -----------------------------
    modules = await conn.fetch("""
        SELECT id, name 
        FROM modules 
        WHERE programme_id = $1
    """, programme_id)

    # -----------------------------
    # 2. Fetch Skills
    # -----------------------------
    skills = await conn.fetch("""
        SELECT id, name 
        FROM skills 
        WHERE programme_id = $1
    """, programme_id)

    # -----------------------------
    # 3. Fetch Module → Skill edges
    # -----------------------------
    module_skill_edges = await conn.fetch("""
        SELECT module_id, skill_id
        FROM module_skills
        WHERE module_id IN (
            SELECT id FROM modules WHERE programme_id = $1
        )
    """, programme_id)

    # -----------------------------
    # 4. Fetch Skill → Skill edges
    # -----------------------------
    skill_relations = await conn.fetch("""
        SELECT source_skill_id, target_skill_id, relation, confidence
        FROM skill_relations
        WHERE programme_id = $1
    """, programme_id)

    # -----------------------------
    # 5. Build Final Graph Response
    # -----------------------------
    nodes = []
    edges = []

    # MODULE NODES
    for m in modules:
        nodes.append({
            "id": str(m["id"]),
            "name": m["name"],
            "type": "module"
        })

    # SKILL NODES
    for s in skills:
        nodes.append({
            "id": str(s["id"]),     # UUID → always STR
            "name": s["name"],
            "type": "skill"
        })

    # MODULE → SKILL EDGES
    for edge in module_skill_edges:
        edges.append({
            "source": str(edge["module_id"]),
            "target": str(edge["skill_id"]),
            "type": "module-skill"
        })

    # SKILL → SKILL RELATION EDGES
    for rel in skill_relations:
        edges.append({
            "source": str(rel["source_skill_id"]),
            "target": str(rel["target_skill_id"]),
            "type": rel["relation"],      # requires | builds_on | complements
            "confidence": float(rel["confidence"])
        })

    # -----------------------------
    # 6. Return Final JSON
    # -----------------------------
    return {
        "nodes": nodes,
        "edges": edges
    }
