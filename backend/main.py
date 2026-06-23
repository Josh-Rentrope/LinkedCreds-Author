from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Union, Optional
import uuid
import sys
import os

import spacy
from spacy.matcher import PhraseMatcher
from skillNer.skill_extractor_class import SkillExtractor
from skillNer.general_params import SKILL_DB

# ---------------------------------------------------------------------------
# Allow imports from the skills-extraction/backend module (skill_graph,
# predict_soc, adjacent_socs, plus the O*NET graph JSON).
# ---------------------------------------------------------------------------
_SKILLS_EXTR_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills-extraction", "backend",
)
if _SKILLS_EXTR_PATH not in sys.path:
    sys.path.insert(0, _SKILLS_EXTR_PATH)

from skill_graph import (
    load_graph, get_skills_for_soc, get_soc_title, get_soc_major_group,
    get_all_soc_codes, get_skill_type,
)
import predict_soc
import adjacent_socs



app = FastAPI()

# Allow front-end requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# load SkillNer once
nlp = spacy.load("en_core_web_lg")
skill_extractor = SkillExtractor(nlp, SKILL_DB, PhraseMatcher)


class TextRequest(BaseModel):
    text: str


class SearchRequest(BaseModel):
    extracted_skills: List[Union[str, Dict[str, Any]]]
    top_k: int = 2


class PredictSOCRequest(BaseModel):
    skills: List[str]
    top_n: int = 5
    include_all: bool = False
    alpha: float = 0.6


class AdjacentSOCRequest(BaseModel):
    soc: str
    top_n: int = 5
    skills: Optional[List[str]] = None
    include_all: bool = False




@app.post("/predict-soc")
def predict_soc_endpoint(request: PredictSOCRequest):
    """Predict the most likely SOC codes for a list of skills.

    Accepts a list of skill names, classifies them into hard/soft,
    and scores candidate SOC codes from the O*NET knowledge graph.
    """
    graph = load_graph()
    idx = {s: s for s in graph["nodes"]["skills"]}
    hard, soft, nf = predict_soc.classify(request.skills, idx)

    if not hard and not soft:
        return {"predictions": [], "not_found": nf}

    preds = predict_soc.predict(
        hard, soft,
        top_n=request.top_n,
        include_all=request.include_all,
        alpha=request.alpha,
    )
    return {"predictions": preds, "not_found": nf}


@app.post("/adjacent-socs")
def adjacent_socs_endpoint(request: AdjacentSOCRequest):
    """Find SOC codes adjacent to a given SOC for upskilling.

    Uses Jaccard similarity over skill overlap to rank adjacent SOCs,
    split into same-category and cross-category results.
    """
    same, cross = adjacent_socs.adjacent(
        request.soc,
        top_n=request.top_n,
        user_skills=request.skills,
        include_all=request.include_all,
    )
    return {"same_category": same, "cross_category": cross}


@app.get("/soc/{soc_code}")
def get_soc_details(soc_code: str):
    """Return metadata and associated skills for an O*NET SOC code."""
    title = get_soc_title(soc_code)
    skills = get_skills_for_soc(soc_code)
    major_group = get_soc_major_group(soc_code)

    hard_skills = [
        s for s in skills
        if get_skill_type(s) in ("technology", "both")
    ]
    soft_skills = [
        s for s in skills
        if get_skill_type(s) in ("soft", "both")
    ]

    return {
        "soc": soc_code,
        "title": title,
        "major_group": major_group,
        "hard_skills": hard_skills,
        "soft_skills": soft_skills,
        "total_skills": len(skills),
    }


@app.on_event("startup")
async def preload_onet_graph():
    """Pre-load the O*NET graph into memory so the first request is fast."""
    load_graph()



# ---------------------------------------------------------------------------
# Mock similar-skills lookup table
# When a real O*NET / FAISS index is not available, this dictionary provides
# plausible "related skill" suggestions so the frontend pipeline can be tested
# end-to-end.  Keys are compared case‑insensitively.
# ---------------------------------------------------------------------------
MOCK_SIMILAR_SKILLS: Dict[str, List[str]] = {
    "python":             ["cython", "jython", "pypy"],
    "javascript":         ["typescript", "coffeescript", "ecmascript"],
    "typescript":         ["javascript", "flow", "es6"],
    "java":               ["kotlin", "scala", "groovy"],
    "kotlin":             ["java", "scala", "groovy"],
    "c++":                ["c", "c#", "objective-c"],
    "c#":                 [".net", "f#", "vb.net"],
    "ruby":               ["jruby", "crystal", "elixir"],
    "php":                ["hack", "perl", "python"],
    "go":                 ["rust", "zig", "c"],
    "rust":               ["go", "c++", "zig"],
    "swift":              ["objective-c", "kotlin", "dart"],
    "dart":               ["flutter", "swift", "kotlin"],
    "r":                  ["matlab", "julia", "sas"],
    "sql":                ["postgresql", "mysql", "sqlite"],
    "mysql":              ["mariadb", "postgresql", "sqlite"],
    "postgresql":         ["mysql", "sqlite", "citus"],
    "mongodb":            ["couchdb", "dynamodb", "firestore"],
    "react":              ["angular", "vue.js", "svelte"],
    "angular":            ["react", "vue.js", "ember.js"],
    "vue.js":             ["react", "angular", "svelte"],
    "svelte":             ["react", "vue.js", "solidjs"],
    "node.js":            ["deno", "bun", "express"],
    "django":             ["flask", "fastapi", "pyramid"],
    "flask":              ["django", "fastapi", "bottle"],
    "fastapi":            ["flask", "django", "starlette"],
    "docker":             ["podman", "kubernetes", "containerd"],
    "kubernetes":         ["docker swarm", "nomad", "openshift"],
    "aws":                ["azure", "gcp", "digitalocean"],
    "azure":              ["aws", "gcp", "ibm cloud"],
    "gcp":                ["aws", "azure", "firebase"],
    "linux":              ["ubuntu", "debian", "centos"],
    "git":                ["mercurial", "subversion", "perforce"],
    "tensorflow":         ["pytorch", "jax", "keras"],
    "pytorch":            ["tensorflow", "jax", "mxnet"],
    "machine learning":   ["deep learning", "nlp", "computer vision"],
    "deep learning":      ["machine learning", "neural networks", "cnn"],
    "nlp":                ["text mining", "sentiment analysis", "transformers"],
    "project management": ["agile", "scrum", "kanban"],
    "agile":              ["scrum", "kanban", "lean"],
    "scrum":              ["agile", "kanban", "safe"],
    "data analysis":      ["data science", "business intelligence", "statistics"],
    "data science":       ["data analysis", "machine learning", "big data"],
    "excel":              ["google sheets", "tableau", "power bi"],
    "tableau":            ["power bi", "looker", "qlik"],
    "power bi":           ["tableau", "excel", "qlik"],
    "photoshop":          ["illustrator", "gimp", "affinity"],
    "illustrator":        ["photoshop", "coreldraw", "affinity designer"],
    "figma":              ["sketch", "adobe xd", "invision"],
    "leadership":         ["management", "mentoring", "team building"],
    "communication":      ["presentation", "writing", "negotiation"],
    "customer service":   ["client relations", "support", "help desk"],
}


@app.post("/extract")
def extract_skills(request: TextRequest):
    text = request.text
    result = skill_extractor.annotate(text)

    skills = set()

    for s in result["results"].get("full_matches", []):
        skills.add(s["doc_node_value"])

    for s in result["results"].get("ngram_scored", []):
        skills.add(s["doc_node_value"])

    extracted_skills_with_source = [
        {
            "name": name,
            "source": "skillner"
        } 
        for name in skills
    ]
    
    return {
        "extracted_skills": extracted_skills_with_source
    }

    #return {"skills": list(skills)}


# Run the app using these commands:
#> python -m venv venv
#> venv/bin/pip install -r requirements.txt
#> venv/bin/python -m spacy download en_core_web_lg
#> venv/bin/uvicorn main:app --reload --port 8000
# http://localhost:8000/extract       -> responds with skills when we provide text as input.
# http://localhost:8000/search        -> returns mocked similar-skill alignments.
# http://localhost:8000/predict-soc   -> predicts SOC codes from a list of skills (O*NET graph)
# http://localhost:8000/adjacent-socs -> finds SOC codes adjacent to a given SOC
# http://localhost:8000/soc/{code}    -> returns metadata & skills for a specific SOC code
# example:
#> curl localhost:8000/extract --json '{"text":"skills text with python and sql"}'
#> curl localhost:8000/search --json '{"extracted_skills":[{"name":"python","source":"skillner"}],"top_k":2}'
#> curl localhost:8000/predict-soc --json '{"skills":["Python","SQL","Machine Learning"],"top_n":3}'
#> curl localhost:8000/adjacent-socs --json '{"soc":"15-1132.00","top_n":5}'
#> curl localhost:8000/soc/15-1132.00
