from fastapi import APIRouter
from pydantic import BaseModel
import os, json
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variable.")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY environment variable.")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

router = APIRouter()

class SkillMap(BaseModel):
    skills: list  # [{"skill":"CAD","score":0.9},...]

@router.post("/suggest-jobs")
def suggest_jobs(payload: SkillMap):
    prompt = (
        f"You are a job recommender for South Africa. Given these skills with strengths: {payload.skills}, "
        "return a JSON array of 6 job objects: "
        "[{\"title\":\"...\",\"match_score\":0.0-1.0,\"required_skills\":[...],\"typical_industries\":[...],\"short_description\":\"...\"}]. "
        "Return JSON only."
    )

    # 1. Use GenerationConfig for structured JSON output (Recommended)
    config = GenerationConfig(
        max_output_tokens=600,
        response_mime_type="application/json"  # Guarantee JSON
    )

    try:
        # 2. Use the recommended generate_content method
        response = model.generate_content(prompt, config=config)
        # The content should be valid JSON due to response_mime_type
        jobs = json.loads(response.text.strip())
    except Exception as e:
        # Log the error and the potentially invalid LLM output for debugging
        print(f"Error parsing JSON from Gemini: {e}")
        # print(f"Raw LLM Response: {getattr(response, 'text', 'N/A')}")
        jobs = []

    # 3. Optimize Supabase Inserts
    job_skill_links = []

    for j in jobs:
        try:
            # Insert job and get the returned row data (including 'id')
            job_data = sb.table("jobs").insert({
                "title": j.get("title"),
                "company": None,
                "source": "gemini",
                "description": j.get("short_description"),
                "match_score": j.get("match_score", 0)
            }).execute().data

            if job_data:
                row_id = job_data[0]["id"]
                # Collect all skill links for bulk insert later
                for sk in j.get("required_skills", []):
                    job_skill_links.append({"job_id": row_id, "skill_name": sk})

        except Exception as e:
            print(f"Error inserting job/skills into Supabase: {e}")

    # 4. Perform a single bulk insert for all job-skill links
    if job_skill_links:
        try:
            # This is significantly more efficient than many single inserts
            sb.table("job_skill_links").insert(job_skill_links).execute()
        except Exception as e:
            print(f"Error bulk inserting job skill links: {e}")

    return {"jobs": jobs}