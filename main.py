import os
import google.generativeai as genai
import json
import time

from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel

from routes.generate import router as generate_router
from routes.programme_graph import router as graph_router

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="SkillPath AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(generate_router, prefix="/api")
app.include_router(graph_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "SkillPath API Connected to Supabase"}

@app.get("/users")
def get_users():
    users = supabase.table("users").select("*").execute()
    return users.data

@app.get("/api/programmes")
def get_programmes():
    res = supabase.table("programmes").select("*").execute()
    return {"programmes": res.data}

@app.get("/api/programmes/{programme_id}")
def get_programme(programme_id: int):
    res = supabase.table("programmes").select("*").eq("id", programme_id).execute()
    if not res.data:
        return {"error": "Programme not found"}
    return {"programme": res.data[0]}

@app.get("/api/programmes/{programme_id}/modules")
def get_programme_modules(programme_id: int):
    res = supabase.table("modules").select("*").eq("programme_id", programme_id).execute()
    return {"programme_id": programme_id, "modules": res.data}

@app.get("/api/programmes/{programme_id}/skills")
def get_programme_skills(programme_id: int):
    res = supabase.table("skills").select("*").eq("programme_id", programme_id).execute()
    return {"programme_id": programme_id, "skills": res.data}

@app.get("/api/modules/{module_id}/skills")
def get_module_skills(module_id: int):
    res = supabase.table("skills").select("*").eq("module_id", module_id).execute()
    return {"module_id": module_id, "skills": res.data}

@app.post("/test-gemini")
def test_gemini():
    response = model.generate_content("A brief hello message")
    return response.text.strip()

@app.post("/api/modules/{module_id}/generate-skills")
def generate_module_skills(module_id: int):
    # 0. Cache check - skip regeneration if skills already exist
    existing_skills = supabase.table("skills").select("id").eq("module_id", module_id).execute()
    if existing_skills.data and len(existing_skills.data) > 0:
        return {
            "module_id": module_id,
            "message": "Skills already exist for this module (cached).",
            "skills_count": len(existing_skills.data)
        }

    # 1. Get module info
    module_res = supabase.table("modules").select("*").eq("id", module_id).execute()
    if not module_res.data:
        return {"error": "Module not found"}
    module = module_res.data[0]

    prompt = f"""
    You are an educational expert. Based on the following module description,
    list 5-10 technical skills and 3-5 transferable skills students develop.

    Module: {module['title']}
    Description: {module['description']}

    Return JSON in this exact format:
    {{
      "technical": ["skill1", "skill2", ...],
      "transferable": ["skill1", "skill2", ...]
    }}
    """

    response = model.generate_content(prompt)
    text = response.text.strip()

    import json, re
    try:
        skills_json = json.loads(text)
    except:
        json_str = re.search(r"\{.*\}", text, re.S)
        if json_str:
            skills_json = json.loads(json_str.group(0))
        else:
            return {"error": "Could not parse Gemini output", "raw": text}

    programme_id = module["programme_id"]
    added, existing = [], []

    # 2. Loop through categories
    for category, skill_list in skills_json.items():
        for skill in skill_list:
            skill_name = skill.strip()

            # Check if it already exists
            existing_check = supabase.table("skills").select("id").eq("module_id", module_id).eq("name", skill_name).execute()
            if existing_check.data:
                existing.append(skill_name)
                continue  # Skip duplicates

            # Insert new
            supabase.table("skills").insert({
                "programme_id": programme_id,
                "module_id": module_id,
                "name": skill_name,
                "category": category
            }).execute()
            added.append(skill_name)

    return {
        "module_id": module_id,
        "module_title": module["title"],
        "added_skills": added,
        "existing_skills": existing
    }

@app.post("/api/programmes/{programme_id}/generate-skills")
def generate_programme_skills(programme_id: int):
    # Check cache first
    cached = supabase.table("skills").select("id").eq("programme_id", programme_id).execute()
    if cached.data and len(cached.data) > 0:
        return {
            "programme_id": programme_id,
            "message": "Skills already exist for this programme (cached).",
            "skills_count": len(cached.data)
        }

    # Get all modules for the programme
    modules_res = supabase.table("modules").select("*").eq("programme_id", programme_id).execute()
    if not modules_res.data:
        return {"error": "No modules found for this programme"}

    # Combine module descriptions
    combined_desc = " ".join(
        [f"{m['title']}: {m['description']}" for m in modules_res.data]
    )

    prompt = f"""
    You are an expert in higher education. Based on the following module descriptions
    from a degree programme, identify 10–15 technical skills and 5–10 transferable skills
    that a student would develop across the programme.

    Programme ID: {programme_id}
    Modules and Descriptions:
    {combined_desc}

    Return JSON in this format:
    {{
      "technical": ["skill1", "skill2", ...],
      "transferable": ["skill1", "skill2", ...]
    }}
    """

    response = model.generate_content(prompt)
    import json, re

    try:
        skills_json = json.loads(response.text.strip())
    except:
        json_str = re.search(r"\{.*\}", response.text.strip(), re.S)
        if json_str:
            skills_json = json.loads(json_str.group(0))
        else:
            return {"error": "Could not parse Gemini output", "raw": response.text}

    # Save results
    added = []
    for category, skill_list in skills_json.items():
        for skill in skill_list:
            skill_name = skill.strip()
            supabase.table("skills").insert({
                "programme_id": programme_id,
                "module_id": None,
                "name": skill_name,
                "category": category
            }).execute()
            added.append(skill_name)

    return {"programme_id": programme_id, "added_skills": added}

@app.get("/api/faculties")
def get_faculties():
    res = supabase.table("faculties").select("*").execute()
    return {"faculties": res.data}

@app.get("/api/faculties/{faculties_id}/programmes")
def get_programmes_by_faculties(faculties_id: int):
    res = supabase.table("programmes").select("*").eq("faculties_id", faculties_id).execute()
    return {"programmes": res.data}

@app.post("/api/programmes/{programme_id}/generate-knowledge-graph")
def generate_knowledge_graph(programme_id: int):
    # Step 1: Get all skills for this programme
    skills_res = supabase.table("skills").select("id, name, category").eq("programme_id", programme_id).execute()
    if not skills_res.data:
        return {"error": "No skills found"}

    skills = [s["name"] for s in skills_res.data]

    # Step 2: Ask Gemini to find relationships
    prompt = f"""
    You are an expert in knowledge graph construction.
    Given this list of skills from an engineering degree:
    {skills}

    Identify meaningful relationships between these skills.
    Examples of relationship types:
    - "requires" (skill A requires skill B)
    - "builds_on" (skill A builds on skill B)
    - "complements" (skill A complements skill B)
    - "applies_to" (skill A applies skill B in context)

    Return the result in JSON:
    {{
      "relations": [
        {{"source": "Skill A", "target": "Skill B", "relation": "requires"}},
        ...
      ]
    }}
    """

    response = model.generate_content(prompt)
    import json, re
    try:
        data = json.loads(response.text.strip())
    except:
        json_str = re.search(r"\{.*\}", response.text, re.S)
        data = json.loads(json_str.group(0)) if json_str else {"relations": []}

    # Step 3: Store relationships in Supabase
    for r in data.get("relations", []):
        supabase.table("skill_relations").insert({
            "programme_id": programme_id,
            "source": r["source"],
            "target": r["target"],
            "relation": r["relation"]
        }).execute()

    return {"programme_id": programme_id, "relations": data.get("relations", [])}

@app.get("/api/programmes/{programme_id}/relations")
def get_programme_relations(programme_id: int):
    res = supabase.table("skill_relations").select("*").eq("programme_id", programme_id).execute()
    return {"relations": res.data}

class RelationResponse(BaseModel):
    source: str
    target: str
    relation: str
    confidence: float = 0.8

# --- Rate limit globals ---
LAST_CALL_TIME = datetime.min
CALL_INTERVAL = 5  # seconds between Gemini calls (~12 RPM max)

def wait_for_slot():
    """Simple rate limiter (max ~12 requests/minute)."""
    global LAST_CALL_TIME
    now = datetime.now()
    delta = (now - LAST_CALL_TIME).total_seconds()
    if delta < CALL_INTERVAL:
        time.sleep(CALL_INTERVAL - delta)
    LAST_CALL_TIME = datetime.now()

# --- Gemini cached request helper ---
def generate_with_cache(prompt: str, cache_key: str, model_name="gemini-2.0-flash"):
    """Check Supabase cache before calling Gemini."""
    cache = (
        supabase.table("ai_cache")
        .select("raw_response")
        .eq("prompt", cache_key)
        .limit(1)
        .execute()
    )
    if cache.data:
        print(f"✅ Cache hit for {cache_key}")
        return cache.data[0]["raw_response"]

    wait_for_slot()

    try:
        print(f"🤖 Calling Gemini for {cache_key} ...")
        response = model.generate_content(prompt)
        text = response.text.strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"raw_text": text}

        supabase.table("ai_cache").insert({
            "model_name": model_name,
            "prompt": cache_key,
            "raw_response": parsed,
        }).execute()

        return parsed
    except Exception as e:
        print("❌ Gemini error:", str(e))
        return {"error": str(e)}

# --- Route ---
@app.post("/api/programmes/{programme_id}/generate-relations")
async def generate_programme_relations(programme_id: int):
    print(f"⚙️ Generating relations for programme {programme_id}...")

    try:
        # 1️⃣ Fetch skills
        skills_resp = supabase.table("skills").select("id, name").eq("programme_id", programme_id).execute()
        skills = skills_resp.data
        print(f"🧩 Found {len(skills)} skills.")

        if not skills:
            raise HTTPException(status_code=404, detail="No skills found for this programme")

        skill_names = [s["name"] for s in skills]

        # 2️⃣ Prepare prompt
        prompt = f"""
        You are an academic AI assistant.
        Given these programme skills:
        {skill_names}

        Create logical relationships between them.
        Use only this JSON structure:
        [
          {{ "source": "Optimization", "target": "Decision Analysis", "relation": "builds_on" }},
          {{ "source": "Systems Thinking", "target": "Operations Research", "relation": "complements" }}
        ]
        """

        cache_key = f"relations_programme_{programme_id}"

        # 3️⃣ Call Gemini (cached)
        print(f"🧠 Sending prompt to Gemini (cache_key={cache_key})...")
        ai_result = generate_with_cache(prompt, cache_key)
        print(f"📩 Gemini returned: {type(ai_result)}")

        # 4️⃣ Parse relations
        relations = []
        if isinstance(ai_result, list):
            relations = ai_result
        elif isinstance(ai_result, dict) and "relations" in ai_result:
            relations = ai_result["relations"]
        elif isinstance(ai_result, dict) and "raw_text" in ai_result:
            try:
                relations = json.loads(ai_result["raw_text"])
            except Exception as e:
                print("⚠️ JSON parse error from raw_text:", str(e))
                relations = []

        if not relations:
            raise HTTPException(status_code=500, detail="No valid relations returned by Gemini")

        print(f"✅ Parsed {len(relations)} relations from Gemini.")

        # 5️⃣ Save new relations (avoid duplicates)
        added_relations = []
        for rel in relations:
            src = next((s for s in skills if s["name"] == rel.get("source")), None)
            tgt = next((s for s in skills if s["name"] == rel.get("target")), None)
            if not src or not tgt:
                continue

            existing = supabase.table("skill_relations") \
                .select("id") \
                .eq("programme_id", programme_id) \
                .eq("source_skill_id", src["id"]) \
                .eq("target_skill_id", tgt["id"]) \
                .execute()

            if existing.data:
                continue

            supabase.table("skill_relations").insert({
                "programme_id": programme_id,
                "source_skill_id": src["id"],
                "target_skill_id": tgt["id"],
                "relation": rel.get("relation", "related_to"),
                "confidence": rel.get("confidence", 0.8)
            }).execute()

            added_relations.append(rel)

        print(f"💾 Added {len(added_relations)} new relations to database.")

        return {
            "programme_id": programme_id,
            "relations_added": len(added_relations),
            "relations": added_relations
        }

    except HTTPException as e:
        print(f"🚫 HTTP Error: {e.detail}")
        raise e
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))