import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(override=True)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_skills_from_modules(programme_name: str, modules: list):
    # modules: list of {"code","title","description"}
    mod_text = "\n".join([f"- {m.get('code','')}: {m.get('title','')} - {m.get('description','')}" for m in modules[:20]])
    prompt = (
        "You are an academic skills extractor. Given the module list for a university engineering degree, "
        "return JSON only in the format: {\"technical\": [...], \"transferable\": [...]}. "
        "List 6-12 technical skills and 4-8 transferable skills. "
        f"Programme: {programme_name}\nModules:\n{mod_text}\n\nJSON:"
    )
    model = genai.models.get("gemini-1.5")  # change per availability
    resp = model.generate_text(prompt=prompt, max_output_tokens=500)
    txt = resp.text.strip()
    try:
        return json.loads(txt)
    except Exception as e:
        # fallback: return empty lists and raw text for manual parsing
        return {"technical": [], "transferable": [], "raw": txt}