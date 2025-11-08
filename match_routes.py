from fastapi import APIRouter
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv
import os
import json

load_dotenv()
SUPABASE_URL = ""
SUPABASE_KEY = ""
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

# Scoring weights: you can tune per-degree or globally
DEFAULT_WEIGHT = 1.0

class SubjectsInput(BaseModel):
    subjects: dict  # {"Mathematics":75, "English":68, ...}
    threshold: float = 0.6  # minimal normalized score to consider showing

# load normalization map
with open("subject_map.json","r",encoding="utf-8") as f:
    SUBJECT_MAP = json.load(f)

def normalize_subject(name:str):
    name = name.strip()
    return SUBJECT_MAP.get(name, name)

@router.post("/match-degrees")
def match_degrees(req: SubjectsInput):
    # normalize user subjects
    user_subjects = {}
    for k,v in req.subjects.items():
        canon = normalize_subject(k)
        try:
            mark = int(v)
        except:
            mark = 0
        user_subjects[canon] = mark

    # get all degrees
    degrees = sb.table("degrees").select("*").execute().data
    # get all course requirements
    reqs = sb.table("course_requirements").select("*").execute().data

    results = []
    for degree in degrees:
        degree_id = degree["id"]
        degree_reqs = [r for r in reqs if r["degree_id"] == degree_id]
        if not degree_reqs:
            continue

        # scoring: for each required subject compute fraction = min(user_mark / req_mark, 1)
        # multiply by weight (default 1). final score = average of fractions
        fractions = []
        missing_reqs = []
        for r in degree_reqs:
            subj = r["subject_name"]
            req_mark = r["minimum_mark"] or 0
            user_mark = user_subjects.get(subj, None)
            if user_mark is None:
                fractions.append(0.0)
                missing_reqs.append(subj)
            else:
                if req_mark <= 0:
                    frac = 1.0
                else:
                    frac = min(user_mark / req_mark, 1.0)
                fractions.append(frac * DEFAULT_WEIGHT)

        # normalized score between 0 and 1
        if fractions:
            score = sum(fractions) / len(fractions)
        else:
            score = 0.0

        results.append({
            "degree_id": degree_id,
            "code": degree["code"],
            "degree": degree["name"],
            "faculty": degree["faculty"],
            "url": degree.get("url"),
            "score": round(score, 3),
            "missing_requirements": missing_reqs
        })

    # sort descending by score
    results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)

    # filter by threshold if requested
    filtered = [r for r in results_sorted if r["score"] >= req.threshold]

    # prepare bubble graph data: nodes (faculty group) and degree nodes
    nodes = []
    links = []
    faculty_nodes = {}
    node_id = 0

    # create faculty nodes first
    faculties = list({r["faculty"] for r in filtered})
    for f in faculties:
        faculty_nodes[f] = f"faculty-{f}"
        nodes.append({
            "id": faculty_nodes[f],
            "label": f,
            "group": "faculty",
            "size": 40
        })

    # degree nodes, linked to their faculty node
    for r in filtered:
        deg_node_id = f"degree-{r['degree_id']}"
        nodes.append({
            "id": deg_node_id,
            "label": f"{r['degree']} ({int(r['score']*100)}%)",
            "group": r["faculty"],
            "size": max(10, int(r["score"]*80)),  # scale size by score
            "url": r.get("url"),
            "score": r["score"],
            "missing_requirements": r["missing_requirements"]
        })
        links.append({
            "source": faculty_nodes[r["faculty"]],
            "target": deg_node_id
        })

    return {
        "results": filtered,
        "bubble": {
            "nodes": nodes,
            "links": links
        }
    }
