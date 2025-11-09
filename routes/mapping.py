from fastapi import APIRouter
from pydantic import BaseModel
import os, json
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import GenerationConfig  # Import for structured output

# --- Configuration ---
load_dotenv(override=True)

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use the recommended GenerativeModel access method
model = genai.GenerativeModel('gemini-1.5-flash')

router = APIRouter()

# --- Schemas ---
class StudentProfile(BaseModel):
    name: str | None = None
    subjects: dict  # {"Mathematics": 78, ...}
    interests: list | None = []
    # ⚠️ CRITICAL FIX: programme_id must be part of the payload
    programme_id: int


# --- API Route ---
@router.post("/map-student")
def map_student(profile: StudentProfile):
    # Fetch programme skills
    # Access profile.programme_id is now safe
    skills = sb.table("programme_skills").select("skill_name").eq("programme_id", profile.programme_id).execute().data
    skill_names = [s["skill_name"] for s in skills]

    prompt = (
        f"You are an expert career mapper. Use the provided subjects/marks and programme skills to estimate student strength in each skill.\n"
        f"Student subjects & marks: {profile.subjects}\n"
        f"Programme skills: {skill_names}\n\nFor each skill, return a JSON array like: "
        "[{\"skill\":\"...\",\"estimated_strength\":0.0-1.0,\"reason\":\"...\"}]. "
        "Estimated_strength should be based on the subjects/marks where relevant.\nReturn JSON only."
    )

    # Use GenerationConfig for modern API call and guaranteed JSON
    config = GenerationConfig(
        max_output_tokens=400,
        response_mime_type="application/json"  # Guarantee JSON
    )

    try:
        # Use the recommended generate_content method
        response = model.generate_content(prompt, config=config)
        skill_map = json.loads(response.text.strip())
    except Exception as e:
        print(f"Error parsing JSON from Gemini: {e}")
        # fallback: uniform medium strength
        skill_map = [{"skill": s, "estimated_strength": 0.5, "reason": "fallback"} for s in skill_names]

    # --- Supabase Inserts ---

    # 1. Insert student and safely retrieve ID
    student_data = sb.table("student_profiles").insert({"name": profile.name}).execute().data

    if not student_data:
        # Handle case where student insert failed (e.g., raise HTTP exception)
        return {"error": "Failed to create student profile"}, 500

    student_id = student_data[0]["id"]

    # 2. Prepare all skill map links for a single bulk insert (OPTIMIZATION)
    skill_map_links = []
    for item in skill_map:
        skill_map_links.append({
            "student_id": student_id,
            "programme_id": profile.programme_id,
            "skill_name": item["skill"],
            "score": item["estimated_strength"]
        })

    # 3. Perform the bulk insert
    if skill_map_links:
        try:
            # Single insert call for all N skills is highly efficient
            sb.table("student_skill_map").insert(skill_map_links).execute()
        except Exception as e:
            print(f"Error bulk inserting student skill map: {e}")

    return {"student_id": student_id, "skill_map": skill_map}