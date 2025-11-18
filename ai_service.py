import asyncio
from typing import List, Dict, Any
from google import genai
from supabase import Client
from models_v2 import GeminiSkillsResponse, ExtractedSkill  # Import your Pydantic models

# --- Configuration ---

# This prompt instructs Gemini on its role and forces a specific JSON output structure.
SYSTEM_PROMPT = """
You are an expert curriculum analyst. Your task is to extract all key technical, soft, and domain-specific skills from the provided university module description.
The output MUST be a valid JSON object conforming exactly to the GeminiSkillsResponse schema.
For 'skill_category', use one of: 'Technical', 'Soft', 'Domain'. For 'ai_confidence', estimate a value between 0.6 and 1.0 based on the description's focus. 
If no skills are found, return an empty 'extracted_skills' list.
"""

async def process_single_module(
        module_data: Dict[str, Any],
        gemini_client: genai.Client,
        supabase_client: Client
):
    """
    Handles the asynchronous process for one module:
    Gemini extraction -> Pydantic validation -> Supabase insertion.
    """
    module_id = module_data['id']
    module_code = module_data['code']
    module_text = module_data['description_text']

    print(f"-> Processing module: {module_code}")

    try:
        # 1. Call Gemini for structured JSON output
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[SYSTEM_PROMPT, f"Module Code: {module_code}\nDescription:\n---\n{module_text}\n---"],
            config={"response_mime_type": "application/json"}
        )

        # 2. Validate and parse the response using the Pydantic model
        structured_data = GeminiSkillsResponse.model_validate_json(response.text)

        # 3. Prepare data for bulk insert into Supabase
        skill_data_for_db = []
        for skill in structured_data.extracted_skills:
            skill_data_for_db.append({
                'module_id': module_id,
                'skill_name': skill.skill_name,
                'skill_category': skill.skill_category,
                'ai_confidence': skill.ai_confidence
            })

        # 4. Save extracted skills to the 'extracted_skills' table
        if skill_data_for_db:
            supabase_client.from_('extracted_skills').insert(skill_data_for_db).execute()

        # 5. Mark module as processed to avoid re-running
        supabase_client.from_('modules').update({'is_processed': True}).eq('id', module_id).execute()

        print(f"<- Successfully processed {module_code}. Inserted {len(skill_data_for_db)} skills.")

    except Exception as e:
        print(f"ERROR: Failed to process module {module_code} (ID: {module_id}). Error: {e}")


async def bulk_process_modules(gemini_client: genai.Client, supabase_client: Client):
    """
    Main function to orchestrate the concurrent AI processing.
    """
    print("--- Starting Bulk AI Processing Job ---")

    # 1. Fetch all unprocessed modules from Supabase
    try:
        result = supabase_client.from_('modules').select('*').eq('is_processed', False).limit(500).execute()
        modules_to_process = result.data
        print(f"Found {len(modules_to_process)} modules to process.")
    except Exception as e:
        print(f"FATAL ERROR: Could not fetch modules from Supabase. {e}")
        return

    if not modules_to_process:
        print("No new modules to process. Job finished.")
        return

    # 2. Create and run concurrent tasks
    tasks = []
    MAX_CONCURRENT_CALLS = 10  # Limit to manage rate limits and resources

    for module in modules_to_process:
        # Create the task
        task = asyncio.create_task(process_single_module(module, gemini_client, supabase_client))
        tasks.append(task)

        # Implement a basic rate limiter/throttle for concurrency management
        # Wait a short period after every MAX_CONCURRENT_CALLS tasks are initiated
        if len(tasks) % MAX_CONCURRENT_CALLS == 0:
            await asyncio.sleep(1.0)

            # Wait for all tasks to complete
    await asyncio.gather(*tasks)
    print("--- Bulk AI Processing Job Complete ---")