from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import yaml, datetime

@dataclass
class Rule:
    name: str
    match: Dict[str, Any]
    dest: str
    options: Dict[str, Any]

def load_rules(path: Path) -> list[Rule]:
    if not path.exists(): return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules: list[Rule] = []
    for r in data.get("rules", []):
        rules.append(Rule(
            name=r.get("name","rule"),
            match=r.get("match",{}),
            dest=r.get("dest","Unsorted"),
            options=r.get("options",{})
        ))
    return rules

def date_tokens(ts: float) -> dict[str,str]:
    dt = datetime.datetime.fromtimestamp(ts)
    return {"year": f"{dt.year:04d}", "month": f"{dt.month:02d}", "day": f"{dt.day:02d}"}

def render_dest(rule: Rule, src: Path, mtime: float, extra: Optional[Dict[str, Any]]=None) -> Path:
    tokens = date_tokens(mtime)
    if extra: tokens.update(extra)
    rel = rule.dest.format(**tokens)
    return Path(rel) / src.name
