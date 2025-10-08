from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class FileEntry:
    path: Path
    is_dir: bool
    size: int
    mtime: float

def iter_tree(root: Path, exclude_roots: set[Path], exclude_dirnames: set[str], max_depth: int = 12):
    root = root.resolve()
    if any(str(root).startswith(str(b.resolve())) for b in exclude_roots):
        return
    stack = [(root, 0)]
    while stack:
        cur, depth = stack.pop()
        try:
            with os.scandir(cur) as it:
                for de in it:
                    try:
                        p = Path(de.path)
                        if de.is_dir(follow_symlinks=False):
                            if p.name in exclude_dirnames:
                                continue
                            mtime = de.stat(follow_symlinks=False).st_mtime
                            yield FileEntry(p, True, 0, mtime)
                            if depth < max_depth:
                                stack.append((p, depth+1))
                        else:
                            st = de.stat(follow_symlinks=False)
                            yield FileEntry(p, False, st.st_size, st.st_mtime)
                    except (PermissionError, FileNotFoundError):
                        continue
        except (NotADirectoryError, PermissionError, FileNotFoundError):
            continue
