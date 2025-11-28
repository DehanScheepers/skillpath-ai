from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from database import get_supabase_client
from clients.gemini_client import generate_json

router = APIRouter(prefix="/api/modules", tags=["Modules"])


@router.post("/{module_id}/process")
async def process_module(
        module_id: int,
        client: Client = Depends(get_supabase_client)
):
    # 1. Fetch Module Details from Supabase
    try:
        # Fetch module and the name of the degree it belongs to
        response = await client.table('modules') \
            .select('id, name, description, degree_id(id, name)') \
            .eq('id', module_id) \
            .single() \
            .execute()

        module_data = response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase Read Error: {e}")

    if not module_data:
        raise HTTPException(status_code=404, detail="Module not found")

    # Unwrap nested degree data
    degree = module_data.pop('degree_id')  # remove degree_id obj from module_data

    # 2. Construct Prompt for Gemini
    prompt = f"""
    You are a curriculum analyst. Extract key skills from this academic module.

    Module Name: {module_data['name']}
    Degree Context: {degree['name']}
    Description: {module_data.get('description', 'No description')}

    Return JSON format:
    {{
        "skills": [
            {{ "name": "Skill Name", "category": "Technical" or "Soft", "description": "Brief reason" }}
        ]
    }}
    """

    # 3. Call AI
    ai_result = await generate_json(prompt)

    if not ai_result or "skills" not in ai_result:
        return {"message": "AI returned no skills", "data": []}

    # 4. Prepare Data for Database Insert
    skills_to_insert = []
    for skill in ai_result['skills']:
        skills_to_insert.append({
            "degree_id": degree['id'],
            "module_id": module_id,
            "name": skill['name'],
            "category": skill['category'],
            "description": skill.get('description', '')
        })

    # 5. Save to Supabase (Upsert to avoid duplicates)
    try:
        await client.table('extracted_skills') \
            .upsert(skills_to_insert, on_conflict='degree_id, module_id, name') \
            .execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase Write Error: {e}")

    return {
        "status": "success",
        "module": module_data['name'],
        "skills_extracted": len(skills_to_insert),
        "skills": skills_to_insert
    }