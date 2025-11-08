from fastapi import APIRouter
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
router = APIRouter()

@router.get("/programmes")
def get_programmes():
    progs = sb.table("programmes").select("*").execute().data
    return progs

@router.get("/programmes/{programme_id}/skills")
def get_programme_skills(programme_id:int):
    skills = sb.table("programme_skills").select("*").eq("programme_id", programme_id).execute().data
    return {"skills": skills}