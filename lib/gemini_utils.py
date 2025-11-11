import time
import json
import os
import google.generativeai as genai
from datetime import datetime, timedelta
from supabase import create_client, Client

# Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# Simple in-memory rate limiter
LAST_CALL_TIME = datetime.min
CALL_INTERVAL = 5  # 1 request every 4-5 seconds ≈ 12/minute max


def wait_for_slot():
    """Ensure we don't exceed 15 requests per minute."""
    global LAST_CALL_TIME
    now = datetime.now()
    delta = (now - LAST_CALL_TIME).total_seconds()
    if delta < CALL_INTERVAL:
        time.sleep(CALL_INTERVAL - delta)
    LAST_CALL_TIME = datetime.now()


def generate_with_cache(prompt: str, cache_key: str, model_name="gemini-1.5-pro"):
    """Check Supabase cache before calling Gemini."""
    # 1️⃣ Check cache first
    cache = (
        supabase_client.table("ai_cache")
        .select("raw_response")
        .eq("prompt", cache_key)
        .limit(1)
        .execute()
    )

    if cache.data:
        try:
            print(f"✅ Cache hit for: {cache_key[:50]}...")
            return cache.data[0]["raw_response"]
        except Exception:
            pass

    # 2️⃣ Wait for available rate slot
    wait_for_slot()

    # 3️⃣ Make Gemini request safely
    print(f"🤖 Calling Gemini for: {cache_key[:50]}...")
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Try parsing JSON
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"raw_text": text}

        # 4️⃣ Cache response in Supabase
        supabase_client.table("ai_cache").insert({
            "model_name": model_name,
            "prompt": cache_key,
            "raw_response": parsed,
        }).execute()

        return parsed

    except Exception as e:
        print("❌ Gemini error:", str(e))
        return {"error": str(e)}
