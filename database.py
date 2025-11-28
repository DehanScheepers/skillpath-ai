import os
from dotenv import load_dotenv
from supabase import acreate_client, Client
from typing import AsyncGenerator

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Global variable for the Supabase Client
SUPABASE_CLIENT: Client = None

async def setup_supabase_client():
    """Initializes the global ASYNCHRONOUS Supabase client."""
    global SUPABASE_CLIENT
    if SUPABASE_CLIENT is None:
        SUPABASE_CLIENT = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase Async Client initialized.")
    return SUPABASE_CLIENT

async def get_supabase_client() -> AsyncGenerator[Client, None]:
    """Dependency: Yields the client for use in endpoints."""
    if SUPABASE_CLIENT is None:
        await setup_supabase_client()
    yield SUPABASE_CLIENT