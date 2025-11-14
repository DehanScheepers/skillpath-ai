async def get_cache(conn, key):
    row = await conn.fetchrow("SELECT raw_response FROM ai_cache WHERE cache_key=$1", key)
    if row:
        return row["raw_response"]
    return None

async def set_cache(conn, key, response):
    await conn.execute(
        "INSERT INTO ai_cache (cache_key, raw_response) VALUES ($1, $2) "
        "ON CONFLICT (cache_key) DO UPDATE SET raw_response=$2",
        key, response
    )
