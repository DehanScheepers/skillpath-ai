from google import genai
import os

client = genai.Client(api_key="")

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Why is the sky blue"
)

print(response.text)