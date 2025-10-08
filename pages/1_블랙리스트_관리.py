import streamlit as st
from pathlib import Path
from aifiler.blacklist import (
    default_blacklist, load_user_blacklist, save_user_blacklist,
    combined_blacklist, EXCLUDE_DIR_NAMES, list_program_dirs,
    list_user_common_dirs, recommend_blacklist_from_scan, list_drive_roots_windows
)
from aifiler.scanner import iter_tree

st.set_page_config(page_title="블랙리스트 관리", layout="wide")
st.title("🛡️ 블랙리스트 관리")

st.markdown("기본 블랙리스트(시스템 보호 경로)는 읽기전용입니다. **사용자 블랙리스트**는 추가/삭제 가능.")

col1, col2 = st.columns(2)
with col1:
    st.subheader("기본 블랙리스트 (읽기전용)")
    for p in sorted(default_blacklist()):
        st.caption(str(p))
with col2:
    st.subheader("사용자 블랙리스트 (편집/삭제 가능)")
    user_set = load_user_blacklist()
    user_list = sorted(str(p) for p in user_set)
    text = st.text_area("사용자 블랙리스트 경로 (줄바꿈 구분)", value="\n".join(user_list), height=200)
    cols = st.columns(3)
    with cols[0]:
        if st.button("저장"):
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            save_user_blacklist(lines)
            st.success("저장 완료")
    with cols[1]:
        # 선택 삭제
        if user_list:
            to_del = st.selectbox("삭제할 경로 선택", options=["(선택)"] + user_list, index=0)
            if st.button("선택 삭제") and to_del != "(선택)":
                new_list = [x for x in user_list if x != to_del]
                save_user_blacklist(new_list)
                st.success(f"삭제 완료: {to_del}")
    with cols[2]:
        if st.button("전체 비우기"):
            save_user_blacklist([])
            st.success("사용자 블랙리스트 전체 삭제")

st.markdown("---")
st.subheader("추천 블랙리스트 (실제 PC 스캔 기반)")
if st.button("추천 계산"):
    with st.spinner("스캔 중..."):
        drives = list_drive_roots_windows()
        recs = recommend_blacklist_from_scan(drives)
    st.session_state["bl_recs"] = [str(p) for p in recs]

recs = st.session_state.get("bl_recs", [])
if recs:
    picked = st.multiselect("추가할 추천 항목 선택", recs)
    if st.button("추천 항목 추가"):
        cur = set(load_user_blacklist())
        for s in picked:
            cur.add(Path(s))
        save_user_blacklist([str(p) for p in sorted(cur)])
        st.success(f"{len(picked)}개 항목 추가 완료")

st.markdown("---")
st.subheader("현재 폴더 트리를 보며 추가하기")
root_str = st.text_input("탐색 루트", value=str(Path.home()))
if st.button("탐색"):
    from aifiler.blacklist import combined_blacklist
    with st.spinner("탐색 중..."):
        entries = list(iter_tree(Path(root_str), combined_blacklist(), EXCLUDE_DIR_NAMES, max_depth=4))
    st.session_state["bl_entries"] = entries

entries = st.session_state.get("bl_entries", [])
if entries:
    dirs = sorted({str(e.path) for e in entries if e.is_dir})
    selected = st.multiselect("블랙리스트로 추가할 폴더 선택", dirs[:5000])
    if st.button("선택 폴더 추가"):
        cur = set(load_user_blacklist())
        for s in selected:
            cur.add(Path(s))
        save_user_blacklist([str(p) for p in sorted(cur)])
        st.success(f"{len(selected)}개 폴더 추가 완료")
