from google import genai
import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

print(f"API Key: {api_key}")

print("--- Loaded Environment Variables ---")
# Only print the variables you care about to keep the output clean
for key in ['SUPABASE_URL', 'SUPABASE_KEY', 'GEMINI_API_KEY']:
    value = os.getenv(key)
    print(f"{key}: {value}")

# To see ALL environment variables (be careful, it's a huge list!):
# print("\n--- Full os.environ dump ---")
# print(os.environ)

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
   model="gemini-2.0-flash",
    contents="Why is the sky blue"
)
print(response.text)