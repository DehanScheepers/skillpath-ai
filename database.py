import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

async def connect():
    return await asyncpg.connect(DB_URL)