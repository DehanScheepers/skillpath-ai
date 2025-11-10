import os
import google.generativeai as genai

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

#from routes.programmes import router as programmes_router
#from routes.mapping import router as mapping_router
#from routes.jobs import router as jobs_router

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="SkillPath AI")
#app.include_router(programmes_router, prefix="/api/old")
#app.include_router(mapping_router, prefix="/api/old")
#app.include_router(jobs_router, prefix="/api/old")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev
    allow_methods=["*"],
    allow_headers=["*"],
)

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