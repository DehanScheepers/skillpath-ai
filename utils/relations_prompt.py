
def build_relations_prompt(skill_list):
    """
    Build a strict prompt for Gemini to generate skill relationships.
    Ensures:
    - JSON only
    - No duplicates
    - Only valid skill IDs returned
    - Uses correct relation types
    """

    return f"""
You are an expert educational skill-mapping system.  
Your goal is to analyze skills in a university programme and determine 
how they relate to each other in a knowledge graph.

Below is a list of skills extracted from the programme:

SKILL LIST:
{skill_list}

Each skill has:
- id (UUID)
- name
- description

---------------------------------
TASK:
---------------------------------
Return a list of relationships BETWEEN these skills.

VALID RELATION TYPES:
- "requires"     → Skill A must be known before Skill B
- "builds_on"    → Skill B enhances or expands Skill A
- "complements"  → Skill A and B are used together often

---------------------------------
IMPORTANT RULES:
---------------------------------
1. You MUST ONLY reference skill IDs that exist in the input list.
2. No self-links (source cannot equal target).
3. No duplicate relations.
4. You must produce only useful relationships.
5. Output must be strictly valid JSON.
6. Output structure must match the schema exactly.

---------------------------------
OUTPUT FORMAT (STRICT):
---------------------------------
{{
  "relations": [
    {{
      "source_skill_id": "uuid",
      "target_skill_id": "uuid",
      "relation": "requires | builds_on | complements",
      "confidence": 0.0 to 1.0
    }}
  ]
}}

---------------------------------
GOOD EXAMPLES:
---------------------------------
If skill: "Statistics"  
and skill: "Probability"  
then relation might be:
- Probability → Statistics ("requires")
- Statistics → Data Analysis ("builds_on")

---------------------------------
NOW GENERATE:
---------------------------------
ONLY return the JSON block.
    """
