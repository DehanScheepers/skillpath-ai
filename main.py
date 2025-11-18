import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from supabase import create_client, Client
from neo4j import GraphDatabase
from google import genai
from typing import List
from ai_service import bulk_process_modules
from models_v2 import Degree, BubbleDiagramData, SkillNode, SkillRelationship
from graph_service import get_skill_suggestions, migrate_to_neo4j
from routers import programmes, modules, graph
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="Skillpath", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(programmes.router)
app.include_router(modules.router)
app.include_router(graph.router)

# Supabase Client
try:
    SUPABASE_CLIENT: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
except Exception as e:
    print(f"ERROR: Could not initialize Supabase Client: {e}")
    SUPABASE_CLIENT = None

# Neo4j Driver
try:
    NEO4J_DRIVER = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
    )
    # Check connectivity
    NEO4J_DRIVER.verify_connectivity()
except Exception as e:
    print(f"ERROR: Could not connect to Neo4j: {e}")
    NEO4J_DRIVER = None

# Gemini Client
try:
    GEMINI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"ERROR: Could not initialize Gemini Client: {e}")
    GEMINI_CLIENT = None


@app.get("/")
def read_root():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "Skill Mapper API is running."}


@app.get("/degrees", response_model=List[Degree])
def list_degrees():
    """Fetches the list of all degrees available from Supabase."""
    if SUPABASE_CLIENT is None:
        raise HTTPException(status_code=503, detail="Database service unavailable.")

    # Check that these lines are correctly indented with 4 spaces (or 1 tab)
    # relative to the function header above it.
    try:
        response = SUPABASE_CLIENT.from_('degress').select('id, name, level').execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@app.post("/admin/run-ai-bulk-job")
async def run_ai_job():
    """Triggers the bulk AI processing of all unprocessed modules."""
    if GEMINI_CLIENT is None or SUPABASE_CLIENT is None:
        raise HTTPException(status_code=503, detail="Required AI or DB services are unavailable.")

    # Run the asynchronous bulk job
    await bulk_process_modules(GEMINI_CLIENT, SUPABASE_CLIENT)

    return {"status": "success", "message": "Bulk AI processing job initiated. Check logs for details."}


@app.post("/skills/suggest", response_model=BubbleDiagramData)
def suggest_skills(user_skills: List[str]):
    """
    Takes a list of skills the user possesses and returns a graph of suggested skills
    and their relationships for the bubble diagram visualization.
    """
    if NEO4J_DRIVER is None:
        raise HTTPException(status_code=503, detail="Graph database service unavailable.")

    # Ensure there are skills to analyze
    if not user_skills:
        raise HTTPException(status_code=400, detail="Please provide a list of user skills for analysis.")

    try:
        # Call the graph service function
        suggestion_data = get_skill_suggestions(NEO4J_DRIVER, user_skills)
        return suggestion_data
    except Exception as e:
        # Log the detailed error (if necessary)
        print(f"Error during skill suggestion: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve skill suggestions from the graph.")


@app.post("/admin/run-neo4j-migration")
def run_neo4j_migration():
    """Triggers the one-time data migration from Supabase to Neo4j,
       and builds the RELATED_TO graph intelligence."""
    if NEO4J_DRIVER is None or SUPABASE_CLIENT is None:
        raise HTTPException(status_code=503, detail="Required DB services are unavailable.")

    # Run the synchronous migration job
    migrate_to_neo4j(SUPABASE_CLIENT, NEO4J_DRIVER)

    return {"status": "success", "message": "Neo4j migration initiated. Check logs for details."}