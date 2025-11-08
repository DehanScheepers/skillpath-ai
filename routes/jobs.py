from fastapi import APIRouter
from pydantic import BaseModel
import os, json
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai
load_dotenv()

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.models.get("gemini-1.5")
router = APIRouter()

class SkillMap(BaseModel):
    skills: list  # [{"skill":"CAD","score":0.9}, ...]

@router.post("/suggest-jobs")
def suggest_jobs(skill_map: SkillMap):
    skills = skill_map.skills
    prompt = (
        f"You are a job recommender. Given these skill names and strengths: {skills}, "
        "return a JSON array of 6 job objects: {title, typical_companies, required_skills, match_score (0-1), short_description} "
        "Rank by match_score desc. Only return JSON."
    )
    resp = model.generate_text(prompt=prompt, max_output_tokens=600)
    try:
        jobs = json.loads(resp.text.strip())
    except Exception:
        jobs = []
    return {"jobs": jobs}