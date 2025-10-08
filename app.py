import streamlit as st
from pathlib import Path
from aifiler.blacklist import combined_blacklist, EXCLUDE_DIR_NAMES, suggested_roots_from_drives_only, list_first_level_dirs
from aifiler.scanner import iter_tree, FileEntry
from aifiler.rules import load_rules
from aifiler.recommender import recommend_rule_for_file, to_move_dest, name_based_label
from aifiler.diff import plan_moves
from aifiler.actions import apply_moves
from aifiler.dupes import find_duplicates
from aifiler.llm_local import prompt_to_rules_yaml
import os, sys, subprocess

st.set_page_config(page_title="AI 파일정리 비서 (MVP)", layout="wide")
st.title("🗂️ AI 파일정리 비서 (MVP)")

# 1) 블랙리스트(기본+사용자)
bl = combined_blacklist()
with st.sidebar:
    st.subheader("블랙리스트(기본 + 사용자)")
    for b in sorted(bl):
        st.caption(str(b))
    st.markdown("---")
    st.caption("※ '블랙리스트 관리' 페이지에서 수정하세요")

# 2) 루트 선택
st.subheader("1) 정리 대상 루트 선택")

# 회사 문서 + 사진 확장자 포함
DOC_EXTS = [".txt",".md",".pdf",".doc",".docx",".ppt",".pptx",".xls",".xlsx",".csv"]
IMG_EXTS = [".jpg",".jpeg",".png",".gif",".bmp",".webp",".tif",".tiff",".heic",".raw"]
DEFAULT_EXTS = DOC_EXTS + IMG_EXTS

ext_multi = st.multiselect("대상 파일 확장자(빈값이면 전체)", DEFAULT_EXTS, default=DEFAULT_EXTS)

# 추천 정리 디렉토리: C:\ / D:\ (1차) → 2차(해당 드라이브의 1단계 폴더)
st.markdown("**추천 정리 디렉토리**")
drives = suggested_roots_from_drives_only()  # C, D만
drive_labels = [str(d) for d in drives] or ["(없음)"]
col1, col2 = st.columns([1,2])
with col1:
    picked_drive = st.selectbox("1) 드라이브 선택", options=drive_labels, index=0)
# 2차 폴더
base_dest_str_default = str(Path.home() / "Organized")
if drives:
    drive_obj = Path(picked_drive)
    first_level = list_first_level_dirs(drive_obj)
    opt2 = ["(드라이브 루트 사용)"] + [str(p) for p in first_level]
    with col2:
        picked_sub = st.selectbox("2) 하위 폴더 선택", options=opt2, index=0)
    if picked_sub == "(드라이브 루트 사용)":
        base_dest_str_default = str(drive_obj / "Organized")
    else:
        base_dest_str_default = str(Path(picked_sub) / "Organized")

# 루트 경로(탐색용)와 정리 대상 루트(결과 위치)를 각각 지정
default_root = str(Path.home())
root_str = st.text_input("탐색 루트 경로", value=default_root)
base_dest_str = st.text_input("정리될 기준 루트(대상)", value=base_dest_str_default)

root = Path(root_str)
base_dest = Path(base_dest_str)

# 2-2) 탐색 버튼
if st.button("폴더 탐색(블랙리스트 제외)"):
    with st.spinner("탐색 중..."):
        entries_all = list(iter_tree(root, bl, EXCLUDE_DIR_NAMES, max_depth=12))
        if ext_multi:
            files_set = set(e.lower() for e in ext_multi)
            entries = [e for e in entries_all if (e.is_dir or e.path.suffix.lower() in files_set)]
        else:
            entries = entries_all
    st.session_state["entries"] = entries
    st.success(f"탐색 완료: {len(entries)}개 항목")
entries = st.session_state.get("entries", [])

if entries:
    st.subheader("2) 인덱스 요약")
    st.write(f"총 항목: {len(entries)} (파일/폴더 포함)")

# 3) 모드 선택
st.subheader("3) 정리 모드 선택")
mode = st.radio("모드", ["자동(미리 설정)", "규칙 설정(AI 추천)", "프롬프트 기반(AI 추천)"])

rules_path = Path("data/rules.yaml")
rules = load_rules(rules_path)
rule_map = {r.name: r for r in rules}

# 프롬프트 → rules.yaml (모델 자동 탐지/다운로드)
MODELS_DIR = Path("models")
if mode == "프롬프트 기반(AI 추천)":
    prompt = st.text_area("정리 방법을 한국어로 작성하세요", height=120,
                          placeholder="예) txt는 문서/{연-월}, 엑셀은 재무/보고서, 사진은 사진/{연/월} ...")
    if st.button("프롬프트로 규칙 생성(내장 LLM)"):
        with st.spinner("규칙 생성 중(모델 자동 탐지/다운로드)…"):
            yml = prompt_to_rules_yaml(prompt, MODELS_DIR)
        st.code(yml, language="yaml")
        if st.button("위 YAML을 rules.yaml로 저장"):
            Path("data").mkdir(exist_ok=True)
            rules_path.write_text(yml, encoding="utf-8")
            rules = load_rules(rules_path)
            st.success("rules.yaml 저장 및 로드 완료")

# 4) 전/후 비교(DRY-RUN) + 중복 알림
st.subheader("4) 전/후 비교 (DRY-RUN)")
use_meta = st.checkbox("초저비용 메타 사용(옵션)", value=False)

move_map = {}
dupes = {}
if st.button("미리보기 생성"):
    if not entries:
        st.warning("먼저 탐색을 실행하세요.")
    else:
        with st.spinner("미리보기와 중복 후보 분석 중..."):
            files = [e for e in entries if not e.is_dir]
            dupes = find_duplicates(files)
            siblings_by_parent: dict[Path, list[FileEntry]] = {}
            for e in files:
                siblings_by_parent.setdefault(e.path.parent, []).append(e)
            for e in files:
                sibs = siblings_by_parent.get(e.path.parent, [])
                rec = {"rule":"others_review","score":0.0,"why":"fallback"}
                if mode == "자동(미리 설정)":
                    lab, sc, _ = name_based_label(e)
                    if lab: rec = {"rule":lab,"score":sc,"why":"auto"}
                else:
                    rec = recommend_rule_for_file(e, sibs, use_meta=use_meta)
                dst = to_move_dest(rule_map, rec, e, base_dest)
                if e.path != dst:
                    move_map[e.path] = dst
            plan = plan_moves(move_map)
        st.session_state["plan"] = plan
        st.session_state["move_map"] = move_map
        st.session_state["dupes"] = dupes
        st.success(f"미리보기 완성: {plan['total']}건 이동 예정")

plan = st.session_state.get("plan")
dupes = st.session_state.get("dupes", {})

# 4-1) 대상 폴더별 개수 + 클릭 시 상세
if plan:
    st.markdown("**대상 폴더별 개수:** (클릭하여 항목 확인)")
    per_dest = plan["per_dest"]
    per_dest_items = plan.get("per_dest_items", {})
    for dest, cnt in sorted(per_dest.items(), key=lambda x: x[0]):
        with st.expander(f"{dest}  —  {cnt}건"):
            items = per_dest_items.get(dest, [])
            for src, dst in items[:500]:
                st.write(f"• {src}  ➜  {dst}")
    st.markdown("**일부 전체 변경 목록:**")
    st.dataframe(plan["changes"][:300])

# 4-2) 중복 후보 그룹 표시
if dupes:
    st.subheader("중복 후보 그룹")
    st.info(f"그룹 수: {len(dupes)}  —  동일 사이즈 + 헤드 해시 기준")
    for i, ((size, hh), group) in enumerate(dupes.items(), start=1):
        with st.expander(f"그룹 #{i} (size={size}, headSHA1={hh})"):
            for e in group:
                st.write(str(e.path))

# 5) 적용 (배치 로그 + 적용 후 탐색기 열기)
st.subheader("5) 적용")
if st.button("변경 적용(이동)"):
    move_map = st.session_state.get("move_map", {})
    if not move_map:
        st.warning("미리보기 후 실행하세요.")
    else:
        applied_log = Path("data/undo.jsonl")
        batch_id = apply_moves(move_map, applied_log, mode="move")
        st.success(f"적용 완료: 배치ID={batch_id}, 이동 파일 {len(move_map)}건")
        # 적용 후 대상 폴더 열기
        try:
            if os.name == "nt":
                os.startfile(str(base_dest))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(base_dest)])
            else:
                subprocess.Popen(["xdg-open", str(base_dest)])
        except Exception:
            pass
        # 세션 정리
        st.session_state.pop("plan", None)
        st.session_state.pop("move_map", None)
        st.session_state.pop("dupes", None)

st.caption("※ 롤백은 좌측 Pages의 '작업 기록 & 롤백' 페이지에서 수행하세요.")
