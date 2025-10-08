from __future__ import annotations
from pathlib import Path
from typing import Iterable, Tuple, Optional, Dict, Any
import re, collections
from .scanner import FileEntry
from .rules import Rule, render_dest
from .meta import cheap_meta_peek

def name_based_label(e: FileEntry) -> Tuple[Optional[str], float, str]:
    ext = e.path.suffix.lower()
    name = e.path.name.lower()
    if ext in {".jpg",".jpeg",".png",".heic"}:
        if re.search(r"(img_|dsc_|screenshot|스크린샷)", name):
            return ("photos_by_date", 0.9, "name:photo")
        return ("photos_by_date", 0.7, "ext:photo")
    if ext == ".pdf":
        if re.search(r"(영수증|청구서|invoice|receipt)", name):
            return ("receipts_pdf", 0.9, "name:receipt")
        return (None, 0.4, "ext:pdf")
    return (None, 0.0, "none")

def neighbor_majority(e: FileEntry, siblings: Iterable[FileEntry]) -> Tuple[Optional[str], float, str]:
    counter = collections.Counter()
    for s in siblings:
        if s is e or s.is_dir: continue
        lab, score, _ = name_based_label(s)
        if lab and score>=0.7: counter[lab]+=1
    if counter:
        lab, cnt = counter.most_common(1)[0]
        return (lab, 0.7 + min(0.2, cnt/50), f"neighbor({cnt})")
    return (None, 0.0, "none")

def recommend_rule_for_file(e: FileEntry, siblings: Iterable[FileEntry], use_meta=False):
    lab, sc, why = name_based_label(e)
    if sc>=0.8 and lab: return {"rule": lab, "score": sc, "why": why}
    lab2, sc2, why2 = neighbor_majority(e, siblings)
    if sc2>=0.7 and lab2: return {"rule": lab2, "score": sc2, "why": why2}
    if use_meta:
        meta_label, meta_score, meta_why = cheap_meta_peek(e.path)
        if meta_label and meta_score>=0.75:
            return {"rule": meta_label, "score": meta_score, "why": meta_why}
    return {"rule":"others_review","score":0.0,"why":"fallback"}

def to_move_dest(rule_map: Dict[str, Rule], rec: Dict[str, Any], e: FileEntry, base_dest: Path) -> Path:
    rname = rec["rule"]
    if rname == "others_review":
        return base_dest / "기타/검토필요" / e.path.name
    rule = rule_map.get(rname)
    if not rule:
        return base_dest / "Unsorted" / e.path.name
    return base_dest / render_dest(rule, e.path, e.mtime)
