"""
skill_graph.py
==============
Read-only data layer for the O*NET knowledge graph.
Loads onet_graph.json into memory and exposes fast lookup functions.
All functions are cached with @lru_cache where appropriate.
"""

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set

GRAPH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "onet_graph.json")

_graph: Optional[Dict[str, Any]] = None


def load_graph() -> Dict[str, Any]:
    """Load (or return cached) the full graph."""
    global _graph
    if _graph is None:
        with open(GRAPH_PATH, "r", encoding="utf-8") as f:
            _graph = json.load(f)
    return _graph


def _g() -> Dict[str, Any]:
    """Shorthand accessor, ensures loaded."""
    return load_graph()


# ── Skill lookups ────────────────────────────────────────────────────────

@lru_cache(maxsize=8192)
def get_skills_for_soc(soc: str) -> List[str]:
    """Return all skill names associated with a SOC code."""
    return _g()["edges"]["soc_to_skill"].get(soc, [])


@lru_cache(maxsize=8192)
def get_socs_for_skill(skill: str) -> List[str]:
    """Return all SOC codes a skill is associated with."""
    return _g()["edges"]["skill_to_soc"].get(skill, [])


def get_all_soc_codes() -> List[str]:
    """Return all unique SOC codes in the graph."""
    return _g()["nodes"]["soc_codes"]


def get_all_skills() -> List[str]:
    """Return all unique skill names."""
    return list(_g()["nodes"]["skills"].keys())


# ── Skill type & metadata ────────────────────────────────────────────────

@lru_cache(maxsize=8192)
def get_skill_type(skill: str) -> str:
    """Return 'technology', 'soft', 'both', or 'unknown'."""
    node = _g()["nodes"]["skills"].get(skill, {})
    return node.get("skill_type", "unknown")


@lru_cache(maxsize=8192)
def is_hot_technology(skill: str) -> bool:
    """Check if a skill is flagged as hot technology."""
    node = _g()["nodes"]["skills"].get(skill, {})
    return bool(node.get("hot_technology", False))


def get_hot_technologies() -> Set[str]:
    """Return the set of all hot technology skill names."""
    return set(_g()["lists"]["hot_technologies"])


def get_skills_by_type() -> Dict[str, List[str]]:
    """Return skills grouped by type: {'technology': [...], 'soft': [...], 'both': [...]}."""
    return _g()["lists"]["skills_by_type"]


# ── SOC titles ───────────────────────────────────────────────────────────

@lru_cache(maxsize=1024)
def get_soc_title(soc: str) -> str:
    """Return the human-readable job title for a SOC code."""
    return _g().get("soc_titles", {}).get(soc, soc)


# ── Soft skill weights ───────────────────────────────────────────────────

@lru_cache(maxsize=4096)
def get_soft_skill_weight(skill_name: str, soc_code: str) -> Optional[Dict[str, float]]:
    """Return {importance, level} for a soft skill in a given SOC, or None."""
    weights = _g().get("soft_skill_weights", {}).get(skill_name, [])
    for entry in weights:
        if entry["soc"] == soc_code:
            return {"importance": entry["importance"], "level": entry["level"]}
    return None


def get_soft_skill_all_weights(skill_name: str) -> List[Dict[str, Any]]:
    """Return all per-SOC weight entries for a soft skill."""
    return _g().get("soft_skill_weights", {}).get(skill_name, [])


# ── Commodity ────────────────────────────────────────────────────────────

def get_commodity_codes() -> List[str]:
    """Return all unique commodity codes."""
    return _g()["nodes"]["commodity_codes"]


@lru_cache(maxsize=4096)
def get_skills_for_commodity(cc: str) -> List[str]:
    """Return skills for a commodity code."""
    return _g()["edges"]["commodity_to_skill"].get(cc, [])


# ── Element IDs ──────────────────────────────────────────────────────────

def get_element_ids() -> List[str]:
    """Return all unique element IDs."""
    return _g()["nodes"]["element_ids"]


@lru_cache(maxsize=256)
def get_skills_for_element(eid: str) -> List[str]:
    """Return skills for an element ID."""
    return _g()["edges"]["element_to_skill"].get(eid, [])


# ── Convenience ──────────────────────────────────────────────────────────

def get_soc_major_group(soc: str) -> str:
    """Return the major group prefix, e.g. '15' from '15-1132.00'."""
    return soc.split("-")[0] if "-" in soc else soc


def get_soc_category_label(soc: str) -> str:
    """Return a category label like '15-xxxx (Computer and Mathematical)'."""
    major = get_soc_major_group(soc)
    return f"{major}-xxxx"


if __name__ == "__main__":
    # Quick self-test
    g = load_graph()
    print(f"Loaded graph: {len(g['nodes']['skills'])} skills, "
          f"{len(g['nodes']['soc_codes'])} SOCs, "
          f"{len(g.get('soc_titles', {}))} titles, "
          f"{len(g.get('soft_skill_weights', {}))} soft-skill elements")
    print(f"Hot technologies: {len(g['lists']['hot_technologies'])}")
    print(f"Sample SOC: 15-1132.00 -> {get_soc_title('15-1132.00')}")
    print(f"Skill 'Python' SOCs: {get_socs_for_skill('Python')[:5]}...")
    print(f"Skill 'Python' type: {get_skill_type('Python')}")
    print(f"Skill 'Python' hot: {is_hot_technology('Python')}")
    sw = get_soft_skill_weight("Critical Thinking", "11-1011.00")
    print(f"Soft weight 'Critical Thinking' for 11-1011.00: {sw}")
