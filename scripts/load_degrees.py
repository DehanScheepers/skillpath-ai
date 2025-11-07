import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://ckjelibfwkvcfgjnzzge.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNramVsaWJmd2t2Y2Znam56emdlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MjQ1MDczMiwiZXhwIjoyMDc4MDI2NzMyfQ.j9UVFFMcwIXacJYLWEaCF87iru-gNf0Uu_-sGbSF4tY"
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

with open("degrees.json", "r", encoding="utf-8") as f:
    degrees = json.load(f)

# Ensure a university row (Stellenbosch)
unis = sb.table("universities").select("*").eq("name", "Stellenbosch University").execute().data
if not unis:
    res = sb.table("universities").insert({"name": "Stellenbosch University", "short": "SU"}).execute()
    university_id = res.data[0]["id"]
else:
    university_id = unis[0]["id"]

for d in degrees:
    # insert degree
    deg = {
        "code": d["code"],
        "name": d["degree"],
        "faculty": d["faculty"],
        "url": d["url"],
        "university_id": university_id
    }
    ins = sb.table("degrees").insert(deg).execute()
    degree_row = ins.data[0]
    degree_id = degree_row["id"]
    # insert requirements
    for subject, mark in d["requirements"].items():
        sb.table("course_requirements").insert({
            "degree_id": degree_id,
            "subject_name": subject,
            "minimum_mark": mark
        }).execute()

print("Degrees loaded.")
