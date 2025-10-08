from __future__ import annotations
import sys, os, string
from pathlib import Path
import yaml
from typing import List, Set, Tuple

USER_BL_PATH = Path("data/blacklist.yaml")

def default_blacklist() -> set[Path]:
    p = sys.platform
    home = Path.home()
    bl: set[Path] = set()
    if p.startswith("win"):
        bl |= {
            Path("C:/Windows"), Path("C:/Program Files"),
            Path("C:/Program Files (x86)"), Path("C:/ProgramData"),
            Path("C:/$Recycle.Bin"), Path("C:/System Volume Information"),
            Path("C:/Recovery"), Path("C:/PerfLogs")
        }
        bl |= {home / "AppData"}
    elif p == "darwin":
        bl |= {Path("/System"), Path("/Applications"), home / "Library"}
    else:
        bl |= {Path("/proc"), Path("/sys"), Path("/dev"), Path("/run"), Path("/var")}
        bl |= {home / ".cache", home / ".local", home / ".config"}
    return bl

EXCLUDE_DIR_NAMES = {
    ".git",".svn",".DS_Store","__pycache__","node_modules","venv",".venv",
    "dist","build",".idea",".vscode"
}

def load_user_blacklist() -> set[Path]:
    if not USER_BL_PATH.exists():
        return set()
    try:
        data = yaml.safe_load(USER_BL_PATH.read_text(encoding="utf-8")) or {}
        paths = data.get("paths", [])
        return {Path(p) for p in paths}
    except Exception:
        return set()

def save_user_blacklist(paths: List[str]) -> None:
    USER_BL_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"paths": [str(Path(p)) for p in paths]}
    USER_BL_PATH.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

def combined_blacklist() -> set[Path]:
    return default_blacklist() | load_user_blacklist()

# ---- 드라이브/루트/추천 계산 ----

def list_drive_roots_windows() -> List[Path]:
    roots: List[Path] = []
    if not sys.platform.startswith("win"):
        return roots
    for letter in string.ascii_uppercase:
        p = Path(f"{letter}:/")
        try:
            if p.exists():
                roots.append(p)
        except Exception:
            pass
    return roots

def list_user_common_dirs() -> List[Path]:
    home = Path.home()
    candidates = [
        home / "Desktop", home / "Documents", home / "Downloads",
        home / "Pictures", home / "Videos", home / "Music",
        home / "OneDrive", home / "Dropbox", home / "Google Drive",
    ]
    return [p for p in candidates if p.exists()]

def list_program_dirs() -> List[Path]:
    p = sys.platform
    progs: List[Path] = []
    if p.startswith("win"):
        for base in ["C:/Program Files", "C:/Program Files (x86)", "C:/ProgramData"]:
            bp = Path(base)
            if bp.exists():
                progs.append(bp)
    elif p == "darwin":
        for base in ["/Applications", "/System/Applications"]:
            bp = Path(base)
            if bp.exists():
                progs.append(bp)
    else:
        for base in ["/usr", "/bin", "/sbin", "/opt", "/snap"]:
            bp = Path(base)
            if bp.exists():
                progs.append(bp)
    return progs

def suggested_roots_from_drives_only() -> List[Path]:
    """
    요구사항: 전체를 탐색한 후 'C:\\, D:\\' 안에 있는 것으로 추천 정리 디렉토리 제시.
    여기서는 실제 존재하는 드라이브 중 C, D 만 1차 후보로 제시.
    """
    roots = []
    if sys.platform.startswith("win"):
        for letter in ["C", "D"]:
            p = Path(f"{letter}:/")
            if p.exists():
                roots.append(p)
    return roots

def list_first_level_dirs(root: Path) -> List[Path]:
    """선택한 드라이브의 1단계 하위 폴더 목록."""
    items: List[Path] = []
    try:
        for entry in root.iterdir():
            if entry.is_dir():
                items.append(entry)
    except Exception:
        pass
    return sorted(items)

# ---- 블랙리스트 추천 ----

SYSTEM_LIKE_NAMES = {
    "Windows","Program Files","Program Files (x86)","ProgramData",
    "$Recycle.Bin","System Volume Information","Recovery","PerfLogs"
}

def recommend_blacklist_from_scan(drives: List[Path]) -> List[Path]:
    """
    실제 PC를 가볍게 스캔하여 블랙리스트 후보 추천:
    - 시스템성 폴더 이름 매치
    - 상위 폴더 내 .exe/.dll 등 실행파일 개수가 많은 폴더
    - 프로그램 설치 루트 (위에서 정의된 program_dirs)
    """
    recs: Set[Path] = set(default_blacklist())
    # 시스템 같은 이름
    for d in drives:
        try:
            for entry in d.iterdir():
                if entry.is_dir() and entry.name in SYSTEM_LIKE_NAMES:
                    recs.add(entry)
        except Exception:
            continue
    # 프로그램 루트
    for p in list_program_dirs():
        recs.add(p)

    # 실행파일 다량 포함 폴더 (최상위 1레벨만 간단히)
    EXT_EXEC = {".exe",".dll",".msi",".sys",".bat",".cmd"}
    for d in drives:
        try:
            for entry in d.iterdir():
                if entry.is_dir() and entry.name not in SYSTEM_LIKE_NAMES:
                    cnt = 0
                    try:
                        for child in entry.iterdir():
                            if child.is_file() and child.suffix.lower() in EXT_EXEC:
                                cnt += 1
                                if cnt >= 20:  # 임계치
                                    recs.add(entry)
                                    break
                    except Exception:
                        pass
        except Exception:
            pass

    # 사용자 블랙리스트와 합치되 중복 제거하여 정렬 반환
    user = load_user_blacklist()
    final: Set[Path] = recs | user
    return sorted(final)
