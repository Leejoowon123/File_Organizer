from __future__ import annotations
from pathlib import Path
import json, shutil, os
from typing import List, Dict, Any, Optional

def read_undo_log(undo_log: Path) -> List[Dict[str, Any]]:
    """배치 단위 레코드를 최신순으로 반환."""
    if not undo_log.exists():
        return []
    lines = [ln for ln in undo_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    recs = [json.loads(x) for x in lines]
    # 오래된 → 최신순으로 저장되어 있으니 최신순으로 뒤집자
    return list(reversed(recs))

def _safe_rmdir(path: Path) -> None:
    """비어있으면 제거. 상위도 비어있게 되면 상위도 정리(너무 위로 올라가지 않도록 제어)."""
    try:
        if path.exists() and path.is_dir():
            # 비어있을 때만 삭제
            if not any(path.iterdir()):
                path.rmdir()
                # 상위 한 단계만 추가로 시도(중첩 생성을 깔끔히)
                parent = path.parent
                if parent.exists() and parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
    except Exception:
        pass

def rollback_batch(undo_log: Path, batch_id: str) -> int:
    """특정 배치 ID를 롤백. 반환: 복원된 파일 수."""
    if not undo_log.exists():
        return 0

    lines = [ln for ln in undo_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    recs = [json.loads(x) for x in lines]

    restored = 0
    kept: List[Dict[str, Any]] = []
    for rec in recs:
        if rec.get("id") == batch_id:
            # 이 배치의 move들을 역순으로 처리(안전)
            for mv in reversed(rec.get("moves", [])):
                src, dst = Path(mv["src"]), Path(mv["dst"])
                if Path(dst).exists():
                    src.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dst), str(src))
                    restored += 1
            # 생성했던 폴더 삭제 시도(비어있을 때만)
            for d in rec.get("created_dirs", []):
                _safe_rmdir(Path(d))
            # 해당 배치 로그는 제거(=미포함)
        else:
            kept.append(rec)

    # kept를 다시 오래된→최신 순서로 기록
    kept_lines = "\n".join(json.dumps(x, ensure_ascii=False) for x in kept)
    undo_log.write_text(kept_lines + ("\n" if kept_lines else ""), encoding="utf-8")
    return restored

def rollback_recent(undo_log: Path, count: Optional[int] = None) -> int:
    """최근 N개 배치를 롤백. 반환: 복원된 파일 총 수."""
    all_batches = read_undo_log(undo_log)  # 최신순
    targets = all_batches if count is None else all_batches[:count]
    total = 0
    for b in targets:
        total += rollback_batch(undo_log, b.get("id", ""))
    return total
