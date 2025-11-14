from fastapi import APIRouter
from database import connect
from clients.gemini_client import generate_json
from utils.cache import get_cache, set_cache

router = APIRouter(prefix="/api/modules")

@router.post("/{module_id}/generate-skills")
async def generate_module_skills(module_id: int):
    conn = await connect()

    module = await conn.fetchrow(
        "SELECT m.id, m.name, p.id AS programme_id, p.name AS programme_name "
        "FROM modules m JOIN programmes p ON m.programme_id = p.id "
        "WHERE m.id=$1", module_id
    )

    cache_key = f"skills_module_{module_id}"
    cached = await get_cache(conn, cache_key)
    if cached:
        return {"cached": True, "skills": cached}

    prompt = f"""
    Extract all key technical and soft skills taught in the module:
    Module name: {module["name"]}
    Programme: {module["programme_name"]}

    Format as JSON:
    {{
        "skills": [
            {{
                "name": "",
                "category": "technical | soft",
                "description": ""
            }}
        ]
    }}
    """

    data = await generate_json(prompt)

    for s in data["skills"]:
        skill = await conn.fetchrow("""
            INSERT INTO skills (programme_id, module_id, name, category, description)
            VALUES ($1,$2,$3,$4,$5)
            ON CONFLICT (programme_id, module_id, name) DO UPDATE SET category=$4, description=$5
            RETURNING id
        """, module["programme_id"], module_id, s["name"], s["category"], s["description"])

        await conn.execute(
            "INSERT INTO module_skills (module_id, skill_id) VALUES ($1,$2) "
            "ON CONFLICT DO NOTHING",
            module_id, skill["id"]
        )

    await set_cache(conn, cache_key, data)
    return data
