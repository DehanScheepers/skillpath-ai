from fastapi import APIRouter, HTTPException
from supabase import create_client
import os
from dotenv import load_dotenv
from ai_recommender import extract_skills_from_modules

load_dotenv(override=True)
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

router = APIRouter()

@router.get("/programmes")
def get_programmes():
    progs = sb.table("programmes").select("*").execute().data
    return progs

@router.get("/programmes/{pid}")
def get_programme(pid:int):
    prog = sb.table("programmes").select("*").eq("id", pid).execute().data
    if not prog:
        raise HTTPException(404, "programme not found")
    modules = sb.table("modules").select("*").eq("programme_id", pid).execute().data
    return {"programme": prog[0], "modules": modules}

@router.post("/programmes/{pid}/extract-skills")
def extract_and_store_skills(pid:int):
    prog = sb.table("programmes").select("*").eq("id", pid).execute().data[0]
    modules = sb.table("modules").select("*").eq("programme_id", pid).execute().data
    skills = extract_skills_from_modules(prog["name"], modules)
    # store skills
    for t in skills.get("technical", []):
        sb.table("programme_skills").insert({"programme_id": pid, "skill_name": t, "skill_type": "technical", "confidence": 0.9}).execute()
    for s in skills.get("transferable", []):
        sb.table("programme_skills").insert({"programme_id": pid, "skill_name": s, "skill_type": "transferable", "confidence": 0.85}).execute()
    return {"stored": True, "skills": skills}