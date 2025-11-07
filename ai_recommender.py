import os

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- AI function ---
def recommend_degrees_from_subjects(subjects: dict):
    prompt = (
        "You are a Stellenbosch University advisor. "
        "Given these subjects and marks: "
        f"{subjects}, suggest 3 undergraduate degrees the student qualifies for. "
        "For each degree, list 3 key skills it builds and 2 potential career paths. "
        "Respond in JSON format with this structure: "
        "{'degree': str, 'skills': [list], 'careers': [list]}"
    )

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()