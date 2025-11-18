from neo4j import GraphDatabase, Driver
from typing import List, Dict, Any
from models_v2 import SkillNode, SkillRelationship, BubbleDiagramData  # Import your API models
from supabase import Client

def get_skill_suggestions(neo4j_driver: Driver, user_skills: List[str]) -> BubbleDiagramData:
    """
    Queries Neo4j to find related skills based on shared module co-occurrence.

    The query works in two parts:
    1. Finds all skills (s2) related to the user's skills (s1).
    2. Calculates the aggregate strength if multiple user skills relate to the same suggested skill.
    """

    # 1. Cypher Query for Skill Relationships
    # UNWIND converts the Python list of user_skills into individual rows for Cypher processing.
    SUGGESTION_CYPHER = """
    UNWIND $user_skills AS u_skill_name
    MATCH (s1:Skill {name: u_skill_name})-[r:RELATED_TO]-(s2:Skill)
    // Filter out suggestions that are already in the user's skill set (s2 not in user_skills)
    WHERE NOT s2.name IN $user_skills 

    // Aggregate the suggestions: group by the suggested skill (s2)
    // and SUM the strength of all incoming RELATED_TO links from the user's skills (s1)
    WITH s2, SUM(r.strength) AS aggregate_strength, COLLECT(s1.name) AS contributing_skills

    // Order by the highest total strength to suggest the most relevant skill first
    ORDER BY aggregate_strength DESC
    LIMIT 10 // Limit to the top 10 suggestions

    RETURN 
        s2.name AS suggested_skill_name, 
        s2.category AS suggested_skill_category, 
        aggregate_strength
    """

    # 2. Cypher Query to find the links for the bubble chart
    # This query finds the links between the user's core skills and the newly suggested skills.
    LINK_CYPHER = """
    MATCH (s1:Skill)-[r:RELATED_TO]-(s2:Skill)
    WHERE s1.name IN $core_skills AND s2.name IN $suggested_skills
    RETURN s1.name AS source, s2.name AS target, r.strength AS strength
    """

    with neo4j_driver.session() as session:
        # A. Get the Top Skill Suggestions
        result = session.run(SUGGESTION_CYPHER, user_skills=user_skills)
        suggested_skills_data = [record for record in result]

        suggested_skill_names = [d['suggested_skill_name'] for d in suggested_skills_data]

        # B. Get the Links between Core Skills and Suggested Skills
        link_result = session.run(LINK_CYPHER, core_skills=user_skills, suggested_skills=suggested_skill_names)
        link_data = [record for record in link_result]

    # 3. Format Data for Pydantic Models (BubbleDiagramData)

    # Create Nodes (Core Skills)
    nodes: List[SkillNode] = []
    for name in user_skills:
        # NOTE: You'd ideally fetch the category for core skills from Supabase or Neo4j too.
        # For simplicity, we assume a default or fetch later.
        nodes.append(SkillNode(
            id=name,
            name=name,
            category="Core",  # Placeholder
            is_core=True
        ))

    # Create Nodes (Suggested Skills)
    for record in suggested_skills_data:
        nodes.append(SkillNode(
            id=record['suggested_skill_name'],
            name=record['suggested_skill_name'],
            category=record['suggested_skill_category'],
            is_suggested=True
        ))

    # Create Links
    links: List[SkillRelationship] = []
    for record in link_data:
        links.append(SkillRelationship(
            source=record['source'],
            target=record['target'],
            strength=record['strength']
        ))

    return BubbleDiagramData(nodes=nodes, links=links)


def migrate_to_neo4j(supabase_client: Client, neo4j_driver: Driver):
    """
    Orchestrates the migration of structured data from Supabase to Neo4j.
    This should be run once, or whenever new extracted_skills are available.
    """

    print("--- Starting Neo4j Migration Job ---")

    # 1. Fetch all extracted skills and their module context from Supabase
    try:
        # Fetch data using the JOIN feature of Supabase (PostgREST)
        # Selects all extracted skills and joins the necessary module data (code, name)
        result = supabase_client.from_('extracted_skills').select('*, modules(code, name)').execute()
        skills_data = result.data
        print(f"Fetched {len(skills_data)} records for migration.")
    except Exception as e:
        print(f"FATAL ERROR: Could not fetch skills from Supabase. {e}")
        return

    # 2. Prepare data for bulk Cypher import
    cypher_params = []
    for skill in skills_data:
        cypher_params.append({
            'module_code': skill['modules']['code'],
            'module_name': skill['modules']['name'],
            'module_id': skill['module_id'],
            'skill_name': skill['skill_name'],
            'skill_category': skill['skill_category'],
            'ai_confidence': skill['ai_confidence'],
        })

    # --- PART A: Create Nodes and TEACHES Relationships ---
    # MERGE is used to create the node if it doesn't exist (UPSERT)
    CREATE_NODES_AND_TEACHES_CYPHER = """
    UNWIND $skills AS item
    // Create or Match the Module Node
    MERGE (m:Module {code: item.module_code})
    ON CREATE SET m.name = item.module_name, m.supabase_id = item.module_id

    // Create or Match the Skill Node
    MERGE (s:Skill {name: item.skill_name})
    ON CREATE SET s.category = item.skill_category

    // Create the TEACHES relationship
    MERGE (m)-[t:TEACHES]->(s)
    ON CREATE SET t.confidence_score = item.ai_confidence
    """

    # --- PART B: Create RELATED_TO Relationships (The Intelligence) ---
    # Finds skills that share a common module and creates a relationship based on co-occurrence count.
    CREATE_RELATED_TO_CYPHER = """
    MATCH (s1:Skill)<-[:TEACHES]-(m:Module)-[:TEACHES]->(s2:Skill)
    WHERE ID(s1) < ID(s2) // Optimization: avoids creating duplicate (s1)-[r]-(s2) and (s2)-[r]-(s1)
    WITH s1, s2, COUNT(m) AS co_occurrence_count

    MERGE (s1)-[r:RELATED_TO]-(s2) 
    ON CREATE SET r.shared_modules = co_occurrence_count, r.strength = toFloat(co_occurrence_count)
    ON MATCH SET r.shared_modules = co_occurrence_count, r.strength = toFloat(co_occurrence_count)
    """

    # 3. Execute queries in a single Neo4j session
    with neo4j_driver.session() as session:
        # Execute Part A
        session.run(CREATE_NODES_AND_TEACHES_CYPHER, skills=cypher_params)
        print("Completed Node and :TEACHES relationship creation.")

        # Execute Part B
        summary = session.run(CREATE_RELATED_TO_CYPHER).consume()
        print(
            f"Completed :RELATED_TO relationship creation. Created/Updated {summary.counters.relationships_created} relations.")

    print("--- Neo4j Migration Job Complete ---")