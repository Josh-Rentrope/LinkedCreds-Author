"""
parse_onet_taxonomy.py
======================
Standalone script to parse O*NET Skills and Technology Skills Excel files,
discover all available columns, build enriched metadata, and generate
reverse-lookup indexes that will later feed into a SQLite knowledge graph.

Usage:
    cd skills-extraction/backend
    python parse_onet_taxonomy.py

Outputs:
    - onet_metadata_enriched.json   (per-skill metadata, same shape as current but enriched)
    - onet_graph.json               (nodes + edges for the knowledge graph)
    - onet_summary.txt              (human-readable summary of what was found)

Keeps the existing API contract: skill names are normalized/stripped, SOC codes
are de-duplicated per skill, UUIDs are deterministic.
"""

import os
import json
import uuid
from collections import defaultdict
from typing import Any, Dict, List

import pandas as pd


# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAXONOMY_DIR = os.path.join(BASE_DIR, "ONet_Skills_Taxonomy")
TECH_SKILLS_PATH = os.path.join(TAXONOMY_DIR, "Technology Skills.xlsx")
SKILLS_PATH = os.path.join(TAXONOMY_DIR, "Skills.xlsx")

OUT_METADATA = os.path.join(BASE_DIR, "onet_metadata_enriched.json")
OUT_GRAPH = os.path.join(BASE_DIR, "onet_graph.json")
OUT_SUMMARY = os.path.join(BASE_DIR, "onet_summary.txt")


# ── Helpers ────────────────────────────────────────────────────────────────

def normalize_name(raw: Any) -> str | None:
    """Strip whitespace; return None for NaN / empty strings."""
    if pd.isna(raw):
        return None
    s = str(raw).strip()
    return s if s else None


def safe_str(raw: Any) -> str:
    """Convert a cell to a trimmed string, returning '' on NaN."""
    if pd.isna(raw):
        return ""
    return str(raw).strip()


def safe_bool(raw: Any) -> bool | None:
    """Interpret a cell as a boolean.  Recognises 'Y'/'Yes'/'y' as True,
    'N'/'No'/'n' as False; returns None otherwise."""
    if pd.isna(raw):
        return None
    s = str(raw).strip().lower()
    if s in ("y", "yes", "true", "1"):
        return True
    if s in ("n", "no", "false", "0"):
        return False
    try:
        return bool(raw)
    except (ValueError, TypeError):
        return None


# ── Discovery: print columns & sample rows ─────────────────────────────────

def discover_excel(path: str, label: str) -> pd.DataFrame:
    """Read an Excel file, print its columns and first rows, return DataFrame."""
    print(f"\n{'='*70}")
    print(f"📂  FILE: {label}")
    print(f"    Path: {path}")
    df = pd.read_excel(path)
    print(f"    Rows: {len(df):,}    Columns: {len(df.columns)}")
    print(f"    Columns: {list(df.columns)}")
    print(f"\n    -- First 5 rows --")
    print(df.head(5).to_string(max_colwidth=60))
    print(f"\n    -- Value counts for key categorical cols --")
    for col in df.columns:
        if df[col].dtype == "object" and df[col].nunique() < 20:
            print(f"    {col}: {dict(df[col].value_counts(dropna=False))}")
    return df



# ── Build enriched metadata ────────────────────────────────────────────────

def build_enriched_metadata(
    df_tech: pd.DataFrame,
    df_skills: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Returns a dict keyed by skill name.

    Each value:
        {
            "soc_codes":       List[str],
            "uuid":            str (urn:uuid:…),
            "element_ids":     List[str],
            "scale_ids":       List[str],
            "categories":      List[str],
            "commodity_codes": List[str],
            "hot_technology":  bool,
            "in_demand":       bool | (omitted if never set),
            "skill_type":      "technology" | "soft" | "both",
        }
    """
    meta: Dict[str, Dict[str, Any]] = {}

    # ── Technology Skills ──────────────────────────────────────────────
    tech_cols = set(df_tech.columns)
    tech_cc_col = next(
        (c for c in tech_cols if "commodity" in c.lower()), None
    )
    tech_hot_col = next(
        (c for c in tech_cols if "hot" in c.lower()), None
    )
    tech_demand_col = next(
        (c for c in tech_cols if "demand" in c.lower()), None
    )

    print(f"\n    [Technology Skills] commodity col = {tech_cc_col!r}")
    print(f"    [Technology Skills] hot col       = {tech_hot_col!r}")
    print(f"    [Technology Skills] demand col    = {tech_demand_col!r}")

    for i in range(len(df_tech)):
        name = normalize_name(df_tech["Example"].values[i])
        if name is None:
            continue

        entry = meta.setdefault(name, dict(
            soc_codes=set(), element_ids=set(), scale_ids=set(),
            categories=set(), commodity_codes=set(),
            hot_technology=False, in_demand=None, skill_type="technology",
        ))

        soc = safe_str(df_tech["O*NET-SOC Code"].values[i])
        if soc:
            entry["soc_codes"].add(soc)

        if tech_cc_col:
            cc = safe_str(df_tech[tech_cc_col].values[i])
            if cc:
                entry["commodity_codes"].add(cc)

        if tech_hot_col:
            hot = safe_bool(df_tech[tech_hot_col].values[i])
            if hot is True:
                entry["hot_technology"] = True

        if tech_demand_col:
            demand = safe_bool(df_tech[tech_demand_col].values[i])
            if demand is not None and entry["in_demand"] is not True:
                entry["in_demand"] = demand

    # ── Soft Skills (Skills.xlsx) ─────────────────────────────────────
    skills_cols = set(df_skills.columns)
    skills_eid_col = next(
        (c for c in skills_cols
         if "element" in c.lower() and "id" in c.lower()), None
    )
    skills_scale_col = next(
        (c for c in skills_cols
         if "scale" in c.lower() and "id" in c.lower()), None
    )
    skills_cat_col = next(
        (c for c in skills_cols if "category" in c.lower()), None
    )

    print(f"\n    [Skills] element ID col  = {skills_eid_col!r}")
    print(f"    [Skills] scale ID col    = {skills_scale_col!r}")
    print(f"    [Skills] category col    = {skills_cat_col!r}")

    for i in range(len(df_skills)):
        name = normalize_name(df_skills["Element Name"].values[i])
        if name is None:
            continue

        if name in meta:
            entry = meta[name]
            if entry["skill_type"] == "technology":
                entry["skill_type"] = "both"
        else:
            entry = meta.setdefault(name, dict(
                soc_codes=set(), element_ids=set(), scale_ids=set(),
                categories=set(), commodity_codes=set(),
                hot_technology=False, in_demand=None, skill_type="soft",
            ))

        soc = safe_str(df_skills["O*NET-SOC Code"].values[i])
        if soc:
            entry["soc_codes"].add(soc)

        if skills_eid_col:
            eid = safe_str(df_skills[skills_eid_col].values[i])
            if eid:
                entry["element_ids"].add(eid)

        if skills_scale_col:
            sid = safe_str(df_skills[skills_scale_col].values[i])
            if sid:
                entry["scale_ids"].add(sid)

        if skills_cat_col:
            cat = safe_str(df_skills[skills_cat_col].values[i])
            if cat:
                entry["categories"].add(cat)

    # ── Finalize: sets → sorted lists, add UUIDs ──────────────────
    for name in meta:
        entry = meta[name]
        entry["soc_codes"] = sorted(entry["soc_codes"])
        entry["element_ids"] = sorted(entry["element_ids"])
        entry["scale_ids"] = sorted(entry["scale_ids"])
        entry["categories"] = sorted(entry["categories"])
        entry["commodity_codes"] = sorted(entry["commodity_codes"])
        entry["uuid"] = uuid.uuid5(uuid.NAMESPACE_DNS, name).urn
        if entry["in_demand"] is None:
            del entry["in_demand"]

    return meta


# ── Build graph indexes (reverse lookups) ──────────────────────────────────

def build_graph_indexes(meta: Dict[str, Any]) -> Dict[str, Any]:
    """From enriched metadata produce nodes + edges suitable for a graph DB."""
    soc_to_skills: Dict[str, List[str]] = defaultdict(list)
    element_to_skills: Dict[str, List[str]] = defaultdict(list)
    commodity_to_skills: Dict[str, List[str]] = defaultdict(list)
    hot_technologies: List[str] = []
    skills_by_type: Dict[str, List[str]] = defaultdict(list)

    skill_to_soc: Dict[str, List[str]] = {}
    skill_to_element: Dict[str, List[str]] = {}
    skill_to_commodity: Dict[str, List[str]] = {}

    for name, entry in meta.items():
        for soc in entry.get("soc_codes", []):
            soc_to_skills[soc].append(name)
            skill_to_soc.setdefault(name, []).append(soc)

        for eid in entry.get("element_ids", []):
            element_to_skills[eid].append(name)
            skill_to_element.setdefault(name, []).append(eid)

        for cc in entry.get("commodity_codes", []):
            commodity_to_skills[cc].append(name)
            skill_to_commodity.setdefault(name, []).append(cc)

        if entry.get("hot_technology"):
            hot_technologies.append(name)

        skills_by_type[entry.get("skill_type", "unknown")].append(name)

    def _sort(d: Dict[str, List[str]]) -> Dict[str, List[str]]:
        return {k: sorted(v) for k, v in d.items()}

    return {
        "nodes": {
            "skills": {
                name: {
                    "uuid": meta[name]["uuid"],
                    "skill_type": meta[name].get("skill_type"),
                    "hot_technology": meta[name].get("hot_technology"),
                }
                for name in sorted(meta.keys())
            },
            "soc_codes": sorted(soc_to_skills.keys()),
            "element_ids": sorted(element_to_skills.keys()),
            "commodity_codes": sorted(commodity_to_skills.keys()),
        },
        "edges": {
            "skill_to_soc":       _sort(skill_to_soc),
            "soc_to_skill":       _sort(soc_to_skills),
            "skill_to_element":   _sort(skill_to_element),
            "element_to_skill":   _sort(element_to_skills),
            "skill_to_commodity": _sort(skill_to_commodity),
            "commodity_to_skill": _sort(commodity_to_skills),
        },
        "lists": {
            "hot_technologies": sorted(hot_technologies),
            "skills_by_type": {
                k: sorted(v) for k, v in skills_by_type.items()
            },
        },
    }


# ── Summary ────────────────────────────────────────────────────────────────

def build_summary(meta: Dict[str, Any], graph: Dict[str, Any]) -> str:
    by_type = graph["lists"]["skills_by_type"]
    lines = [
        "O*NET Taxonomy Parse Summary",
        "=" * 50,
        f"Total unique skills:     {len(meta):,}",
        f"  - Technology:          {len(by_type.get('technology', [])):,}",
        f"  - Soft:                {len(by_type.get('soft', [])):,}",
        f"  - Both:                {len(by_type.get('both', [])):,}",
        "",
        f"Total unique SOC codes:   "
        f"{len(graph['nodes']['soc_codes']):,}",
        f"Total unique Element IDs: "
        f"{len(graph['nodes']['element_ids']):,}",
        f"Total unique Commodity codes: "
        f"{len(graph['nodes']['commodity_codes']):,}",
        "",
        f"Hot technologies:         "
        f"{len(graph['lists']['hot_technologies']):,}",
    ]
    hot_sample = graph["lists"]["hot_technologies"][:10]
    if hot_sample:
        lines.append(f"  Sample: {hot_sample}")
    lines.append("")

    with_soc = sum(1 for e in meta.values() if e.get("soc_codes"))
    with_eid = sum(1 for e in meta.values() if e.get("element_ids"))
    with_cc = sum(1 for e in meta.values() if e.get("commodity_codes"))
    with_cat = sum(1 for e in meta.values() if e.get("categories"))
    with_scale = sum(1 for e in meta.values() if e.get("scale_ids"))
    lines += [
        f"Skills with SOC codes:      {with_soc:,}",
        f"Skills with Element IDs:    {with_eid:,}",
        f"Skills with Commodity codes:{with_cc:,}",
        f"Skills with Categories:     {with_cat:,}",
        f"Skills with Scale IDs:      {with_scale:,}",
        "",
        "-- Sample enriched metadata entries --",
    ]
    for i, (name, entry) in enumerate(meta.items()):
        if i >= 5:
            break
        lines.append(f"\n  [{name}]")
        for k, v in entry.items():
            if isinstance(v, list) and len(v) > 6:
                lines.append(f"    {k}: [{len(v)} items] {v[:3]} ...")
            else:
                lines.append(f"    {k}: {v}")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("🔍  O*NET Taxonomy Parser")
    print(f"    Base directory: {BASE_DIR}")

    # 1. Discover columns
    df_tech = discover_excel(TECH_SKILLS_PATH, "Technology Skills.xlsx")
    df_skills = discover_excel(SKILLS_PATH, "Skills.xlsx")

    # 2. Build enriched metadata
    print("\n" + "=" * 70)
    print("🏗  Building enriched metadata …")
    meta = build_enriched_metadata(df_tech, df_skills)

    # 3. Build graph indexes
    print("\n🔗  Building graph indexes …")
    graph = build_graph_indexes(meta)

    # 4. Write outputs
    print(f"\n💾  Writing outputs …")
    with open(OUT_METADATA, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"    ✅ {OUT_METADATA}")

    with open(OUT_GRAPH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"    ✅ {OUT_GRAPH}")

    summary = build_summary(meta, graph)
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"    ✅ {OUT_SUMMARY}")
    print(f"\n{summary}")


if __name__ == "__main__":
    main()
