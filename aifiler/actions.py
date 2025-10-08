from __future__ import annotations
from pathlib import Path
import shutil, json, datetime, os
from typing import Dict, List, Tuple

def _open_folder_in_explorer(path: Path) -> None:
    """플랫폼별로 폴더 열기."""
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", str(path)])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass

def apply_moves(move_map: Dict[Path, Path], undo_log: Path, mode: str = "move") -> str:
    """
    한 번의 '적용' 버튼 클릭을 배치 1건으로 기록.
    로그 레코드 구조:
    {
      "id": "<ISO-날짜시간>_<counter>",
      "time": "...",
      "mode": "move",
      "moves": [ {"src": "...", "dst": "..."} , ... ],
      "created_dirs": ["...", "..."]   # 이번 적용 중 새로 만든 폴더들
    }
    반환값: 생성된 batch_id
    """
    undo_log.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.utcnow().isoformat()
    batch_id = now.replace(":", "").replace("-", "").replace(".", "")

    created_dirs: set[Path] = set()
    moves_rec: List[Dict[str, str]] = []

    # 실제 이동
    for src, dst in move_map.items():
        dst_parent = dst.parent
        if not dst_parent.exists():
            dst_parent.mkdir(parents=True, exist_ok=True)
            created_dirs.add(dst_parent)
        if mode == "move":
            shutil.move(str(src), str(dst))
        elif mode == "copy":
            shutil.copy2(str(src), str(dst))
        else:
            shutil.move(str(src), str(dst))
        moves_rec.append({"src": str(src), "dst": str(dst)})

    record = {
        "id": batch_id,
        "time": now,
        "mode": mode,
        "moves": moves_rec,
        "created_dirs": [str(p) for p in sorted(created_dirs)],
    }

    with undo_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return batch_id
