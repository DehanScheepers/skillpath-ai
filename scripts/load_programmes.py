# scripts/load_programmes.py
import json, os
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

with open("programmes_clean.json","r",encoding="utf-8") as f:
    programmes = json.load(f)

# ensure university exists
res = sb.table("universities").select("*").eq("name","Stellenbosch University").execute().data
if not res:
    un = sb.table("universities").insert({"name":"Stellenbosch University","short":"SU"}).execute().data[0]
    uni_id = un["id"]
else:
    uni_id = res[0]["id"]

for p in programmes:
    deg = {
        "code": p.get("code"),
        "name": p["name"],
        "faculty": p.get("faculty","Engineering"),
        "url": p.get("url"),
        "university_id": uni_id
    }
    ins = sb.table("programmes").insert(deg).execute().data[0]
    prog_id = ins["id"]
    for mod in p.get("modules",[]):
        sb.table("modules").insert({
            "programme_id": prog_id,
            "code": mod.get("code"),
            "title": mod.get("title"),
            "description": mod.get("description")
        }).execute()

print("Loaded programmes and modules.")