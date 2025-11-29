from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from database import get_supabase_client  # Assuming this dependency is available

router = APIRouter(prefix="/api/degrees", tags=["Degrees"])

@router.get("/")
async def get_all_degrees(
        client: Client = Depends(get_supabase_client)
):
    """
    Fetches a list of all available degrees (programmes) from the database,
    returning their IDs and names. This is used to populate the dropdown
    in the frontend.
    """
    try:
        # Fetch all degrees. Assuming the table is named 'degrees' and
        # contains 'id' and 'name' columns.
        query_result = await client.table('degrees') \
            .select('id, name') \
            .execute()

        degrees_data = query_result.data

        if not degrees_data:
            # Return an empty list if the table exists but is empty
            return []

        return degrees_data

    except Exception as e:
        print(f"Supabase Read Error during degree fetch: {e}")
        # Return a 500 status code if the database read fails
        raise HTTPException(status_code=500, detail=f"Database read failed: {e}")