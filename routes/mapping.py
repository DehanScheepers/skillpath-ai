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

class StudentProfile(BaseModel):
    name: str | None = None
    subjects: dict  # {"Mathematics": 78, ...}
    interests: list | None = []

@router.post("/map-student")
def map_student(profile: StudentProfile):
    # 1) decide programme skills to compare with — this endpoint expects client to pass programme_id or name
    # For simplicity here assume client passes programme_id in subjects dict: {"_programme_id": 3, ...}
    prog_id = profile.subjects.pop("_programme_id", None)
    if not prog_id:
        return {"error":"Please include _programme_id key in subjects with programme id."}

    # load programme skills
    skills = sb.table("programme_skills").select("*").eq("programme_id", prog_id).execute().data
    # basic mapping: technical skill strength = average of related subject marks if subject keywords match
    # Build a prompt to let Gemini score student vs skills
    prompt = (
        f"You are an expert career mapper. A student has these subjects and marks: {profile.subjects}. "
        f"Programme id {prog_id} has skills: {', '.join([s['skill_name'] for s in skills])}. "
        "For each skill, produce a JSON object with 'skill', 'estimated_strength' (0-1) and short reason. "
        "Strength should be based on how the subjects relate to the skill (e.g., Math supports 'modelling'). "
        "Return JSON array."
    )
    resp = model.generate_text(prompt=prompt, max_output_tokens=400)
    try:
        skill_map = json.loads(resp.text.strip())
    except Exception:
        # fallback simple mapping: set all skills to 0.5
        skill_map = [{"skill":s["skill_name"], "estimated_strength":0.5, "reason":"fallback"} for s in skills]

    # optionally store student and map
    student = sb.table("student_profiles").insert({"name": profile.name}).execute().data[0]
    for sm in skill_map:
        sb.table("student_skill_map").insert({
            "student_id": student["id"],
            "programme_id": prog_id,
            "skill_name": sm["skill"],
            "score": sm["estimated_strength"]
        }).execute()
    return {"student_id": student["id"], "skill_map": skill_map}