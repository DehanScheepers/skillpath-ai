# scripts/load_industrial.py
import json, os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(override=True)
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
sb = create_client(URL, KEY)

# path to the uploaded file in this environment or your repo
with open("files/IndustrialTestValues.txt","r",encoding="utf-8") as f:
    data = json.load(f)

# ensure university row
uni = sb.table("universities").select("*").eq("name","Stellenbosch University").execute().data
if not uni:
    uni_row = sb.table("universities").insert({"name":"Stellenbosch University","short":"SU"}).execute().data[0]
    uni_id = uni_row["id"]
else:
    uni_id = uni[0]["id"]

for prog in data:
    deg = {
        "code": "BENG-IND",
        "name": prog["programme"],
        "faculty": prog.get("faculty","Engineering"),
        "url": None,
        "university_id": uni_id
    }
    inserted = sb.table("programmes").insert(deg).execute().data[0]
    pid = inserted["id"]
    for m in prog["modules"]:
        sb.table("modules").insert({
            "programme_id": pid,
            "code": m.get("code"),
            "title": m.get("title"),
            "description": m.get("description")
        }).execute()

print("Loaded Industrial Engineering programme into Supabase.")
