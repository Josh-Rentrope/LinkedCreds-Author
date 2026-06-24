#!/usr/bin/env python3
"""adjacent_socs.py - Find SOC codes adjacent to a given SOC for upskilling."""
import argparse, json, sys, os
from typing import Any, Dict, List, Set

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_graph import (
    load_graph, get_socs_for_skill, get_skills_for_soc, get_soc_title,
    get_skill_type, get_hot_technologies, get_soc_major_group,
)


def jaccard(set_a: Set[str], set_b: Set[str]) -> float:
    union = set_a | set_b
    inter = set_a & set_b
    return len(inter) / len(union) if union else 0.0


def idf_weight(skill: str) -> float:
    n = len(get_socs_for_skill(skill))
    return 1.0 / max(1, n)


def adjacent(soc, top_n=5, user_skills=None, include_all=False):
    hot_set = get_hot_technologies()
    soc_all = set(get_skills_for_soc(soc))
    soc_h = {s for s in soc_all if get_skill_type(s) in ("technology","both")}
    soc_s = {s for s in soc_all if get_skill_type(s) in ("soft","both")}
    if not include_all:
        soc_h = {s for s in soc_h if s in hot_set}
    soc_eff = soc_h | soc_s
    user_set = set(user_skills) if user_skills else set()
    all_socs = [s for s in load_graph()["nodes"]["soc_codes"] if s != soc]
    results = []
    for o in all_socs:
        o_all = set(get_skills_for_soc(o))
        o_h = {s for s in o_all if get_skill_type(s) in ("technology","both")}
        o_s = {s for s in o_all if get_skill_type(s) in ("soft","both")}
        if not include_all:
            o_h = {s for s in o_h if s in hot_set}
        o_eff = o_h | o_s
        sim = jaccard(soc_eff, o_eff)
        ov = soc_eff & o_eff
        df = o_eff - soc_eff
        un = soc_eff - o_eff
        td = sorted(df, key=lambda s: idf_weight(s), reverse=True)[:10]
        tc = sorted(ov, key=lambda s: idf_weight(s), reverse=True)[:10]
        results.append({
            "soc": o, "title": get_soc_title(o),
            "major_group": get_soc_major_group(o),
            "same_category": get_soc_major_group(o) == get_soc_major_group(soc),
            "jaccard": round(sim, 4),
            "overlap_count": len(ov),
            "differentiating_count": len(df),
            "top_overlap": tc,
            "top_differentiating": td,
            "unique_to_current": sorted(un, key=lambda s: idf_weight(s), reverse=True)[:5],
        })
    results.sort(key=lambda x: (x["jaccard"], x["differentiating_count"]), reverse=True)
    same_cat = [r for r in results if r["same_category"]]
    cross_cat = [r for r in results if not r["same_category"]]
    return same_cat[:top_n], cross_cat[:top_n]


def fmt(same, cross, soc, title):
    lines = [f"Adjacent SOCs to {soc} ({title})", "=" * 60]
    lines.append(f"\n  Same Category ({get_soc_major_group(soc)}-xxxx):")
    if not same: lines.append("    (none)")
    for i, r in enumerate(same, 1):
        lines.append(f"    {i}. {r['soc']}  {r['title']}")
        lines.append(f"       Jaccard: {r['jaccard']:.3f}  Overlap: {r['overlap_count']}  New: {r['differentiating_count']}")
        lines.append(f"       Top overlap: {', '.join(r['top_overlap'][:5])}")
        lines.append(f"       Differentiating: {', '.join(r['top_differentiating'][:5])}")
    lines.append(f"\n  Cross-Category:")
    if not cross: lines.append("    (none)")
    for i, r in enumerate(cross, 1):
        lines.append(f"    {i}. {r['soc']}  {r['title']}  (Group: {r['major_group']}-xxxx)")
        lines.append(f"       Jaccard: {r['jaccard']:.3f}  Overlap: {r['overlap_count']}  New: {r['differentiating_count']}")
        lines.append(f"       Top overlap: {', '.join(r['top_overlap'][:5])}")
        lines.append(f"       Differentiating: {', '.join(r['top_differentiating'][:5])}")
    return "\n".join(lines)

def main():
    p = argparse.ArgumentParser(description="Find adjacent SOC codes")
    p.add_argument("--soc", type=str, required=True, help="SOC code, e.g. 15-1132.00")
    p.add_argument("--skills", type=str, help="JSON list of user skills")
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--include-all-tech", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    us = json.loads(args.skills) if args.skills else None
    title = get_soc_title(args.soc)
    same, cross = adjacent(args.soc, args.top_n, us, args.include_all_tech)
    if args.json:
        print(json.dumps({"same_category": same, "cross_category": cross}, indent=2))
    else:
        print(fmt(same, cross, args.soc, title))

if __name__ == "__main__":
    main()
