import os
import json
import re
from google import genai
from google.genai import types

# Initialize globally (setup in main.py lifespan usually, but lazy loading here works too)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


async def generate_json(prompt: str):
    """
    Sends a prompt to Gemini and cleans the response to ensure valid JSON.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )

        # Parse the JSON response
        return json.loads(response.text)

    except Exception as e:
        print(f"Gemini Generation Error: {e}")
        # Return empty structure on failure to prevent app crash
        return {"skills": []}