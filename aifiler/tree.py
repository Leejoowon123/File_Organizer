from __future__ import annotations
from collections import defaultdict
from typing import Any
from .scanner import FileEntry

def build_tree(entries: list[FileEntry]) -> dict[str, Any]:
    root: dict[str, Any] = {"files": [], "dirs": defaultdict(lambda: {"files": [], "dirs": defaultdict(dict)})}
    for e in entries:
        parts = e.path.parts
        node = root
        for part in parts[:-1]:
            node = node["dirs"][part]
        if e.is_dir:
            node["dirs"][e.path.name]
        else:
            node["files"].append({"name": e.path.name, "size": e.size, "mtime": e.mtime, "path": str(e.path)})
    return root
