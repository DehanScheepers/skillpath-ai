import os

from fastapi import APIRouter
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@router.post("/recommend-course")
def recommend_course(subjects: dict):
    """
    Input example:
    {
        "Mathematics": 75,
        "English": 60,
        "Physical Science": 65,
        "Life Orientation": 80,
        "History": 55,
        "Afrikaans": 50,
        "IT": 70,
        "Life Sciences": 58
    }
    """
    # Get all course requirements
    data = supabase.table("course_requirements").select("*").execute().data
    degrees = supabase.table("degrees").select("*").execute().data

    recommendations = []

    for degree in degrees:
        degree_id = degree["id"]
        degree_reqs = [r for r in data if r["degree_id"] == degree_id]

        # Check if user meets all requirements
        meets_all = True
        for req in degree_reqs:
            user_mark = subjects.get(req["subject_name"], 0)
            if user_mark < req["minimum_mark"]:
                meets_all = False
                break

        if meets_all:
            recommendations.append(degree["name"])

    return {
        "qualified_degrees": recommendations if recommendations else ["No degrees matched your marks."]
    }
