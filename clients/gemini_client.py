import google.generativeai as genai
import json
import os
import asyncio

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.0-flash"

async def generate_json(prompt: str):
    await asyncio.sleep(2)  # rate limit safety

    response = genai.GenerativeModel(MODEL).generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )

    text = response.text
    return json.loads(text)