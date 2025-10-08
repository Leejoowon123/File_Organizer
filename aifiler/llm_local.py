from __future__ import annotations
from pathlib import Path
from typing import Optional, List
from ruamel.yaml import YAML
import glob

try:
    from gpt4all import GPT4All  # pip install gpt4all
except Exception as e:
    raise RuntimeError("gpt4all가 설치되어 있어야 합니다: pip install gpt4all") from e

_GPT: Optional[GPT4All] = None

# 기본적으로 찾을 모델 파일명 후보 (없으면 첫 번째 *.gguf 사용)
DEFAULT_MODEL_NAME_CANDIDATES: List[str] = [
    "qwen2.5-3b-instruct.Q4_K_M.gguf",
    "qwen2.5-3b-instruct-q4_k_m.gguf",
    "Qwen2.5-3B-Instruct.Q4_K_M.gguf",
]

SYS_PROMPT = (
  "You are a converter that ONLY outputs JSON per the schema below. "
  "User will describe file-organization rules in Korean or English. "
  "Return compact JSON that fits this Python schema:\n"
  "{ 'rules': [ { 'name': str, 'match': { 'ext'?: [str], 'name_like'?: [str] }, "
  "'dest': str, 'options'?: { 'conflict'?: 'rename'|'skip'|'overwrite' } } ] }\n"
  "Do not add comments. Do not add extra keys. Do not use YAML. JSON only."
)

def _discover_model(models_dir: Path) -> tuple[str, Path]:
    """
    models 폴더에서 *.gguf를 자동 탐지.
    1) 후보 파일명 우선 매칭
    2) 없으면 임의의 첫 GGUF 사용
    반환: (model_file_name, models_dir)
    """
    models_dir.mkdir(parents=True, exist_ok=True)
    all_gguf = [Path(p) for p in glob.glob(str(models_dir / "*.gguf"))]
    # 1) 후보 우선
    for name in DEFAULT_MODEL_NAME_CANDIDATES:
        p = models_dir / name
        if p.exists():
            return (p.name, models_dir)
    # 2) 첫 번째 아무 GGUF
    if all_gguf:
        return (all_gguf[0].name, models_dir)
    # 3) 없으면 기본 후보 중 하나의 이름만 반환(다운로드 용)
    return (DEFAULT_MODEL_NAME_CANDIDATES[0], models_dir)

def _ensure_model(model_file_or_name: str, model_dir: Path):
    """
    gpt4all은 (모델파일명, 모델디렉터리)로 생성 시,
    - 해당 파일이 있으면 그대로 사용
    - 없으면 같은 이름을 가진 모델을 인터넷에서 자동 다운로드 시도
    """
    global _GPT
    if _GPT is None:
        _GPT = GPT4All(model_file_or_name, model_dir.as_posix())

def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 3:
            return parts[1].strip()
    return t

def _json_to_yaml(json_text: str) -> str:
    import json
    data = json.loads(json_text)
    yaml = YAML()
    yaml.default_flow_style = False
    from io import StringIO
    buf = StringIO()
    yaml.dump(data, buf)
    return buf.getvalue()

def prompt_to_rules_yaml(prompt: str, models_dir: Path) -> str:
    """
    프롬프트 -> (gpt4all 내장 LLM) JSON -> YAML
    - models_dir 에서 모델 자동 탐지
    - 파일이 없어도 같은 이름을 가진 모델 자동 다운로드 시도
    """
    model_file_name, mdir = _discover_model(models_dir)
    _ensure_model(model_file_name, mdir)
    assert _GPT is not None
    sys_prompt = SYS_PROMPT + "\nOutput MUST be valid JSON. No markdown fences."
    out = _GPT.generate(
        f"{sys_prompt}\nUSER:\n{prompt}\nJSON:",
        max_tokens=512,
        temp=0.1
    )
    json_text = _strip_code_fences(out)
    return _json_to_yaml(json_text)
