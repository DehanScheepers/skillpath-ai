import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from supabase import acreate_client, Client
from google import genai
from routers import modules
from routers import analysis_endpoints as analysis_router
from routers import degrees as degree_router
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

SUPABASE_CLIENT: Client = None
GEMINI_CLIENT = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global SUPABASE_CLIENT, GEMINI_CLIENT

    print("--- 🚀 Application Startup Initiating ---")

    # 1. Supabase Client Setup (Asynchronous)
    try:
        SUPABASE_CLIENT = acreate_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        print("✅ Supabase Client initialized.")
    except Exception as e:
        print(f"❌ ERROR: Could not initialize Supabase Client: {e}")
        SUPABASE_CLIENT = None


    # 3. Gemini Client Setup
    try:
        GEMINI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        print("✅ Gemini Client initialized.")
    except Exception as e:
        print(f"❌ ERROR: Could not initialize Gemini Client: {e}")
        GEMINI_CLIENT = None

    print("--- 🟢 Application Startup Complete ---")

    yield  # Application continues running

    # --- Shutdown Code ---
    # Supabase and Gemini clients usually don't require an explicit close
    print("--- 🔴 Application Shutdown Complete ---")


# Pass the lifespan function to the FastAPI app constructor
app = FastAPI(title="Skillpath", version="1.0.0", lifespan=lifespan)

# --- Middleware and Router Setup (Unchanged) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(modules.router)
app.include_router(analysis_router, prefix="/api")
app.include_router(degree_router)

@app.get("/")
def read_root():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "Skill Mapper API is running."}
