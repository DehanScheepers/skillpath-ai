# scripts/generate_programme_skills.py
import os, json
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
from supabase import create_client

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.models.get("gemini-1.5")  # adjust model name per availability

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

programmes = sb.table("programmes").select("*").execute().data

for prog in programmes:
    modules = sb.table("modules").select("*").eq("programme_id", prog["id"]).execute().data
    # build a prompt summarizing modules
    mod_text = "\n".join([f"{m['code'] or ''} - {m['title']}: {m['description'] or ''}" for m in modules[:12]])  # limit size
    prompt = (
        f"You are an academic skills extractor. Given the following module titles and descriptions for the degree '{prog['name']}', "
        "return a JSON object with two arrays: 'technical' and 'transferable'. Each array should contain skill names (no more than 15 total). "
        "Respond ONLY with JSON.\n\n"
        f"Modules:\n{mod_text}\n\nJSON OUTPUT:"
    )
    resp = model.generate_text(prompt=prompt, max_output_tokens=600)  # adapt to SDK usage
    text = resp.text.strip()
    try:
        skills = json.loads(text)
    except Exception as e:
        print("Failed to parse JSON for", prog["name"])
        print(text)
        continue

    # insert into DB
    for s in skills.get("technical",[]):
        sb.table("programme_skills").insert({
            "programme_id": prog["id"],
            "skill_name": s,
            "skill_type": "technical",
            "confidence": 0.9
        }).execute()
    for s in skills.get("transferable",[]):
        sb.table("programme_skills").insert({
            "programme_id": prog["id"],
            "skill_name": s,
            "skill_type": "transferable",
            "confidence": 0.85
        }).execute()
    print("Saved skills for", prog["name"])