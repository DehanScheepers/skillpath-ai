import os
from supabase import create_client
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import APIRouter
import json, re

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.0-flash"  # adjust to available model

router = APIRouter()

def parse_json_from_text(text: str):
    try:
        return json.loads(text)
    except:
        m = re.search(r'\{.*\}', text, re.S)
        return json.loads(m.group(0)) if m else None

@router.post("/modules/{module_id}/generate-skills")
def generate_module_skills(module_id: int):
    # Fetch module data
    mod = supabase.table("modules").select("*").eq("id", module_id).execute().data
    if not mod:
        return {"error": "Module not found"}
    mod = mod[0]

    # Check if module already has skills
    existing = supabase.table("module_skills").select("skill_id").eq("module_id", module_id).execute().data
    if existing:
        skill_ids = [r['skill_id'] for r in existing]
        skills = supabase.table("skills").select("*").in_("id", skill_ids).execute().data
        return {"module_id": module_id, "cached": True, "skills": skills}

    # AI prompt
    prompt = f"""
    You are an educational expert. Given this module, return JSON:
    {{"technical": ["skill1", "skill2"], "transferable": ["skill3"]}}
    Module title: {mod['title']}
    Description: {mod['description']}
    Return JSON only.
    """
    model = genai.GenerativeModel(MODEL_NAME)
    resp = model.generate_content(prompt)
    skills_json = parse_json_from_text(resp.text.strip())
    if not skills_json:
        return {"error": "Failed to parse AI output", "raw": resp.text}

    # Insert skills + links
    added = []
    for cat, list_sk in skills_json.items():
        for s in list_sk:
            s_name = s.strip()
            existing_skill = supabase.table("skills").select("id").eq("programme_id", mod["programme_id"]).eq("module_id", module_id).eq("name", s_name).execute().data
            if existing_skill:
                skill_id = existing_skill[0]["id"]
            else:
                new_skill = supabase.table("skills").insert({
                    "programme_id": mod["programme_id"],
                    "module_id": module_id,
                    "name": s_name,
                    "category": cat
                }).execute().data[0]
                skill_id = new_skill["id"]

            supabase.table("module_skills").upsert({
                "module_id": module_id,
                "skill_id": skill_id
            }).execute()
            added.append(s_name)

    return {"module_id": module_id, "added": added}
