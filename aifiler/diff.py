from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict

def plan_moves(move_map: Dict[Path, Path]) -> Dict[str, Any]:
    total = len(move_map)
    per_dest_count: dict[str,int] = {}
    per_dest_items: dict[str, List[Tuple[str,str]]] = defaultdict(list)
    changes = []
    for src, dst in move_map.items():
        rec = {"src": str(src), "dst": str(dst)}
        changes.append(rec)
        key = str(dst.parent)
        per_dest_count[key] = per_dest_count.get(key, 0) + 1
        per_dest_items[key].append((str(src), str(dst)))
    return {
        "total": total,
        "per_dest": per_dest_count,
        "per_dest_items": per_dest_items,
        "changes": changes
    }
