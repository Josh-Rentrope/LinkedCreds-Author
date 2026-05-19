from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Union
import uuid
import spacy
from spacy.matcher import PhraseMatcher
from skillNer.skill_extractor_class import SkillExtractor
from skillNer.general_params import SKILL_DB

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

    # Return format matching what the frontend skillsApi.ts expects
    return {
        "extracted_skills": [
            {"name": name, "source": "skillner"}
            for name in skills
        ]
    }


def _get_mock_alignments(skill_name: str, top_k: int = 2) -> List[Dict[str, Any]]:
    """Return a list of mocked alignment dicts for *skill_name*.

    If the skill is found in MOCK_SIMILAR_SKILLS (case‑insensitive),
    up to *top_k* related skills are returned.  Otherwise an empty list
    is returned so the frontend still receives a valid response.
    """
    key = skill_name.strip().lower()
    similar = MOCK_SIMILAR_SKILLS.get(key, [])[:top_k]

    alignments: List[Dict[str, Any]] = []
    for i, related in enumerate(similar):
        score = round(0.95 - i * 0.10, 2)  # 0.95, 0.85, …
        alignments.append({
            "type": ["Alignment"],
            "targetFramework": "SkillNer",
            "similarity score": score,
            "targetCode": [],
            "targetName": related,
            "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"{skill_name}::{related}").urn,
        })
    return alignments


@app.post("/search")
def search_skills(request: SearchRequest):
    """Map skill names to related skills (mock implementation).

    Accepts the same payload shape as the Ollama‑based backend so the
    frontend requires zero changes.  Returns stubbed alignment entries
    from the MOCK_SIMILAR_SKILLS dictionary (empty alignment for unknown
    skills).
    """
    skills_response: List[Dict[str, Any]] = []

    for skill_item in request.extracted_skills:
        skill_name = skill_item["name"] if isinstance(skill_item, dict) else skill_item
        skill_source = skill_item.get("source", "skillner") if isinstance(skill_item, dict) else "skillner"

        alignments = _get_mock_alignments(skill_name, request.top_k)

        skills_response.append({
            "name": skill_name,
            "source": skill_source,
            "alignment": alignments,
        })

    return {"skill": skills_response}


# Run the app using these commands:
#> python -m venv venv
#> venv/bin/pip install -r requirements.txt
#> venv/bin/python -m spacy download en_core_web_lg
#> venv/bin/uvicorn main:app --reload --port 8000
# http://localhost:8000/extract -> responds with skills when we provide text as input.
# http://localhost:8000/search  -> returns mocked similar-skill alignments.
# example:
#> curl localhost:8000/extract --json '{"text":"skills text with python and sql"}'
#> curl localhost:8000/search --json '{"extracted_skills":[{"name":"python","source":"skillner"}],"top_k":2}'
