#!/usr/bin/env python3
"""predict_soc.py - CLI for SOC code prediction from skills."""
import argparse, json, sys, os, ast
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_graph import (
    load_graph, get_socs_for_skill, get_skills_for_soc, get_soc_title,
    get_skill_type, get_hot_technologies, get_soft_skill_weight,
    get_soc_major_group, get_all_soc_codes,
)


def find_skill(name: str, idx: Dict[str, str]) -> str | None:
    if name in idx:
        return idx[name]
    lower = name.lower()
    for canon in idx:
        if canon.lower() == lower:
            return canon
    return None


def classify(skill_names: List[str], idx: Dict[str, str]) -> Tuple[List[str], List[str], List[str]]:
    hard, soft, nf = [], [], []
    for raw in skill_names:
        canon = find_skill(raw.strip(), idx)
        if canon is None:
            nf.append(raw)
            continue
        st = get_skill_type(canon)
        if st in ("technology", "both"):
            hard.append(canon)
        if st in ("soft", "both"):
            soft.append(canon)
    return hard, soft, nf


def score_soc(soc, user_hard, user_soft, alpha, include_all, hot_set):
    soc_skills = get_skills_for_soc(soc)
    soc_hard, soc_soft = set(), set()
    for s in soc_skills:
        st = get_skill_type(s)
        if st in ("technology", "both"):
            soc_hard.add(s)
        if st in ("soft", "both"):
            soc_soft.add(s)
    uh_set = set(user_hard)
    if not include_all:
        soc_hard = {s for s in soc_hard if s in hot_set or s in uh_set}
    mh = uh_set & soc_hard
    denom = min(len(uh_set), len(soc_hard))
    hs = len(mh) / denom if denom > 0 else 0.0
    ms, tsw = [], 0.0
    for ss in set(user_soft):
        w = get_soft_skill_weight(ss, soc)
        if w and w["importance"] > 0:
            tsw += w["importance"] / 5.0
            ms.append(ss)
    ss_val = tsw / max(1, len(set(user_soft)))
    total = alpha * hs + (1 - alpha) * ss_val
    mh_miss = sorted(soc_hard - uh_set, key=lambda s: len(get_socs_for_skill(s)))
    ms_miss = sorted(soc_soft - set(user_soft), key=lambda s: len(get_socs_for_skill(s)))
    return {
        "soc": soc, "title": get_soc_title(soc),
        "major_group": get_soc_major_group(soc),
        "total_score": round(total, 4), "hard_score": round(hs, 4),
        "soft_score": round(ss_val, 4),
        "matched_hard": sorted(mh), "matched_soft": ms,
        "missing_hard": mh_miss[:10], "missing_soft": ms_miss[:5],
        "soc_hard_count": len(soc_hard), "soc_soft_count": len(soc_soft),
    }


def predict(user_hard, user_soft, top_n=5, include_all=False, alpha=0.6):
    hot_set = get_hot_technologies()
    cands: Set[str] = set()
    for sk in user_hard + user_soft:
        for soc in get_socs_for_skill(sk):
            cands.add(soc)
    if not cands:
        print("Warning: no candidate SOCs, falling back to all.")
        cands = set(get_all_soc_codes())
    scored = [score_soc(s, user_hard, user_soft, alpha, include_all, hot_set) for s in cands]
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored[:top_n]


def extract_ollama(text):
    try:
        from ollama import chat
    except ImportError:
        print("Error: ollama not installed. pip install ollama")
        sys.exit(1)
    SYS = "Extract ONLY professional skills from text. Output JSON list. No explanations."
    resp = chat(model="qwen2.5:7b", messages=[
        {"role": "system", "content": SYS},
        {"role": "user", "content": text},
    ])
    content = resp.message.content.replace("```json","").replace("```","").strip()
    try:
        sk = ast.literal_eval(content)
        return sk if isinstance(sk, list) else []
    except (ValueError, SyntaxError):
        return []


def fmt(preds, nf):
    lines = ["=" * 72, "  SOC Code Prediction Results", "=" * 72]
    if nf:
        lines.append(f"\n  Not in O*NET: {', '.join(nf)}")
    lines.append("")
    for i, p in enumerate(preds, 1):
        lines.append(f"  {i}. {p['soc']}  {p['title']}")
        lines.append(f"     Score: {p['total_score']:.3f} (hard={p['hard_score']:.3f} soft={p['soft_score']:.3f})")
        lines.append(f"     Group: {p['major_group']}-xxxx")
        if p["matched_hard"]:
            lines.append(f"     Matched hard: {', '.join(p['matched_hard'])}")
        if p["matched_soft"]:
            lines.append(f"     Matched soft: {', '.join(p['matched_soft'])}")
        if p["missing_hard"]:
            lines.append(f"     Missing hard (top 5): {', '.join(p['missing_hard'][:5])}")
        if p["missing_soft"]:
            lines.append(f"     Missing soft: {', '.join(p['missing_soft'][:5])}")
        lines.append(f"     SOC sizes: {p['soc_hard_count']}h/{p['soc_soft_count']}s")
        lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Predict O*NET SOC codes")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--skills", type=str, help="JSON list of skills")
    g.add_argument("--text", type=str, help="Free text for Ollama extraction")
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--include-all-tech", action="store_true")
    p.add_argument("--alpha", type=float, default=0.6)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.text:
        print("Extracting via Ollama...")
        names = extract_ollama(args.text)
        print(f"Extracted: {names}")
    else:
        names = json.loads(args.skills)
    if not names:
        print("No skills."); sys.exit(0)

    idx = {s: s for s in load_graph()["nodes"]["skills"]}
    uh, us, nf = classify(names, idx)
    print(f"\nHard: {uh}\nSoft: {us}")
    if nf:
        print(f"Not in O*NET: {nf}")
    if not uh and not us:
        print("No matches."); sys.exit(0)

    preds = predict(uh, us, args.top_n, args.include_all_tech, args.alpha)
    if args.json:
        print(json.dumps(preds, indent=2))
    else:
        print(fmt(preds, nf))


if __name__ == "__main__":
    main()
