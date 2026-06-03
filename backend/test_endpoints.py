#!/usr/bin/env python3
"""test_endpoints.py  —  Test the new O*NET/SOC endpoints via the Python requests library.

Usage:
    pip install requests
    python test_endpoints.py

Set BASE_URL env var to change target, e.g.:
    BASE_URL=http://localhost:8000 python test_endpoints.py
"""

import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


def request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except URLError as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return {"error": str(e)}


def heading(n: int, title: str) -> None:
    bar = "=" * 46
    print(f"\n{bar}")
    print(f" {n}. {title}")
    print(bar)


def main() -> None:
    # 1. Predict SOC (basic)
    heading(1, "POST /predict-soc  \u2014 basic prediction")
    r1 = request("POST", "/predict-soc", {
        "skills": ["Python", "SQL", "Machine Learning", "Project Management"],
        "top_n": 3,
    })
    print(json.dumps(r1, indent=2))

    # 2. Predict SOC (custom alpha)
    heading(2, "POST /predict-soc  \u2014 custom alpha + include_all")
    r2 = request("POST", "/predict-soc", {
        "skills": ["Python", "Java", "C++"],
        "top_n": 5,
        "alpha": 0.8,
        "include_all": True,
    })
    print(json.dumps(r2, indent=2))

    # 3. Predict SOC (unknown skills)
    heading(3, "POST /predict-soc  \u2014 unknown skills only")
    r3 = request("POST", "/predict-soc", {
        "skills": ["Frobnication", "Widget Smithing"],
        "top_n": 3,
    })
    print(json.dumps(r3, indent=2))

    # 4. Adjacent SOCs
    heading(4, "POST /adjacent-socs  \u2014 find adjacent SOCs")
    r4 = request("POST", "/adjacent-socs", {
        "soc": "15-1132.00",
        "top_n": 5,
    })
    print(json.dumps(r4, indent=2))

    # 5. Adjacent SOCs with user skills
    heading(5, "POST /adjacent-socs  \u2014 with user skills")
    r5 = request("POST", "/adjacent-socs", {
        "soc": "15-1132.00",
        "top_n": 3,
        "skills": ["Python", "Kubernetes", "AWS"],
    })
    print(json.dumps(r5, indent=2))

    # 6. SOC details
    heading(6, "GET /soc/{code}  \u2014 SOC details")
    r6 = request("GET", "/soc/15-1132.00")
    print(json.dumps(r6, indent=2))

    # 7. SOC details (another SOC)
    heading(7, "GET /soc/{code}  \u2014 another SOC")
    r7 = request("GET", "/soc/11-1011.00")
    print(json.dumps(r7, indent=2))

    print(f"\n{'=' * 46}")
    print(" Done.")
    print(f"{'=' * 46}\n")


if __name__ == "__main__":
    main()
