import streamlit as st
from pathlib import Path
from aifiler.undo import read_undo_log, rollback_recent, rollback_batch

st.set_page_config(page_title="작업 기록 & 롤백", layout="wide")
st.title("📝 작업 기록 & 롤백 (배치 단위)")

LOG_PATH = Path("data/undo.jsonl")

st.subheader("배치 기록")
batches = read_undo_log(LOG_PATH)  # 최신순
st.write(f"총 {len(batches)} 건 (한 번의 '적용' 클릭 = 1건)")

if batches:
    # 표 요약: 배치ID, 시간, 파일 개수
    view = [{"batch_id":b.get("id",""), "time":b.get("time",""), "files":len(b.get("moves",[])), "mode":b.get("mode","")} for b in batches]
    st.dataframe(view[:1000])

    st.markdown("### 특정 배치 롤백")
    ids = ["(선택)"] + [b.get("id","") for b in batches]
    pick = st.selectbox("배치 ID 선택", options=ids, index=0)
    if st.button("선택 배치 롤백") and pick != "(선택)":
        n = rollback_batch(LOG_PATH, pick)
        st.success(f"복원 파일 수: {n}")

    st.markdown("### 최근 N건 롤백")
    n = st.number_input("N 입력", min_value=1, value=1, step=1)
    if st.button("최근 N건 롤백"):
        cnt = rollback_recent(LOG_PATH, count=int(n))
        st.success(f"복원 파일 수: {cnt}")
else:
    st.info("아직 작업 기록이 없습니다.")
