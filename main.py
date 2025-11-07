import os

from fastapi import FastAPI
from supabase import create_client, Client
from dotenv import load_dotenv
import google.generativeai as genai
from course_routes import router as course_router
from pydantic import BaseModel
from ai_recommender import recommend_degrees_from_subjects
from match_routes import router as match_router

load_dotenv()

app = FastAPI(title="SkillPath AI")
app.include_router(match_router, prefix="/api")

client = genai.configure(api_key="AIzaSyA7ejkpnIirZhh6GyGcem_gKTEk3l8-BJs")

SUPABASE_URL = "https://ckjelibfwkvcfgjnzzge.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNramVsaWJmd2t2Y2Znam56emdlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjQ1MDczMiwiZXhwIjoyMDc4MDI2NzMyfQ.j9UVFFMcwIXacJYLWEaCF87iru-gNf0Uu_-sGbSF4tY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app.include_router(course_router)

@app.get("/")
def root():
    return {"message": "SkillPath API Connected to Supabase"}

@app.get("/users")
def get_users():
    users = supabase.table("users").select("*").execute()
    return users.data

class SubjectInput(BaseModel):
    subjects: list[str]
    marks: list[int]

@app.post("/test-gemini")
def test_gemini():
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("A brief hello message")
    return response.text.strip()

@app.post("/recommend-courses/")
async def recommend_courses(data: SubjectInput):
    subjects = data.subjects
    marks = data.marks

    # Example logic: average mark threshold
    avg_mark = sum(marks) / len(marks)

    # Simple placeholder logic for now
    if avg_mark >= 80 and "Maths" in subjects:
        return {"eligible_courses": ["Engineering", "Computer Science"]}
    elif avg_mark >= 70:
        return {"eligible_courses": ["Commerce", "Social Science"]}
    else:
        return {"eligible_courses": ["Arts", "Humanities"]}

class SubjectsInput(BaseModel):
    subjects: dict

@app.post("/recommend-degrees-ai")
async def recommend_degrees(data: SubjectsInput):
    recommendations = recommend_degrees_from_subjects(data.subjects)
    return {"recommendations": recommendations}