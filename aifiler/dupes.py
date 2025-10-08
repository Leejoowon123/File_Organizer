from __future__ import annotations
from pathlib import Path
import hashlib
from collections import defaultdict
from .scanner import FileEntry

def head_hash(path: Path, n_bytes=1024*1024) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        h.update(f.read(n_bytes))
    return h.hexdigest()

def find_duplicates(files: list[FileEntry]):
    bins = defaultdict(list)
    for e in files:
        if e.is_dir: continue
        try:
            hh = head_hash(e.path)
            bins[(e.size, hh)].append(e)
        except Exception:
            continue
    return {k:v for k,v in bins.items() if len(v)>=2}
