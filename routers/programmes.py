from fastapi import APIRouter
from database import connect
from clients.gemini_client import generate_json
from utils.cache import get_cache, set_cache
from utils.relations_prompt import build_relations_prompt

router = APIRouter(prefix="/api/programme")

@router.post("/{programme_id}/generate-relations")
async def generate_relations(programme_id: int):
    conn = await connect()

    skills = await conn.fetch(
        "SELECT id, name, description FROM skills WHERE programme_id=$1",
        programme_id
    )

    skill_list = [{"id": s["id"], "name": s["name"], "description": s["description"]} for s in skills]

    cache_key = f"relations_programme_{programme_id}"
    cached = await get_cache(conn, cache_key)
    if cached:
        return {"cached": True, "relations": cached}

    prompt = build_relations_prompt(skill_list)
    data = await generate_json(prompt)

    for r in data["relations"]:
        await conn.execute("""
            INSERT INTO skill_relations (programme_id, source_skill_id, target_skill_id, relation, confidence)
            VALUES ($1,$2,$3,$4,$5)
        """, programme_id, r["source_skill_id"], r["target_skill_id"], r["relation"], r["confidence"])

    await set_cache(conn, cache_key, data)
    return data
