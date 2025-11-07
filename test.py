from google import genai
import os

client = genai.Client(api_key="AIzaSyA7ejkpnIirZhh6GyGcem_gKTEk3l8-BJs")

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Why is the sky blue"
)

print(response.text)