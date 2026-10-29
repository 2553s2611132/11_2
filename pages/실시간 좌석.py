import streamlit as st
import pandas as pd
import random

# 페이지 기본 설정
st.set_page_config(
    page_title="천안오성고 급식실 실시간 좌석 현황판",
    page_icon="🍱",
    layout="wide"
)

# 학교 타이틀 및 정보
st.title("🍱 천안오성고등학교 급식실 실시간 좌석 현황판")
st.caption("🏫 천안오성고 재학생(1,267명) 및 급식실 조리사 선생님을 위한 실시간 좌석 관리 시스템")

# 데이터 세션 상태 초기화
TOTAL_STUDENTS = 1267  # 천안오성고 전체 학생 수
SEAT_ROWS = 8          # 8행
SEAT_COLS = 40         # 40열 (총 320석: 동시 수용 인원)

if "seats_df" not in st.session_state:
    data = []
    random.seed(42)
    for r in range(1, SEAT_ROWS + 1):
        for c in range(1, SEAT_COLS + 1):
            table_no = ((c - 1) // 4) + 1
            # 빈자리 / 식사중 2가지 상태만 사용
            status = random.choice(["🟢 빈자리", "🔴 식사중", "🔴 식사중"])
            data.append({
                "행": r,
                "열": c,
                "좌석번호": f"{r}-{c}",
                "테이블": f"테이블 {table_no}",
                "상태": status
            })
    st.session_state.seats_df = pd.DataFrame(data)

if "today_served" not in st.session_state:
    st.session_state.today_served = 420  # 현재 기준 식사 완료 학생 수

df = st.session_state.seats_df

# 사이드바 - 관리자 제어판
st.sidebar.header("👩‍🍳 급식 관리자 제어판")
st.sidebar.info(f"🏫 **천안오성고 전체 학생 수**: {TOTAL_STUDENTS:,}명")

st.sidebar.subheader("1. 식사 완료 학생 카운트")
c_col1, c_col2 = st.sidebar.columns(2)
with c_col1:
    if st.sidebar.button("➕ 학생 +1명 입실"):
        if st.session_state.today_served < TOTAL_STUDENTS:
            st.session_state.today_served += 1
            st.rerun()
with c_col2:
    if st.sidebar.button("➕ 학급 +30명 입실"):
        if st.session_state.today_served + 30 <= TOTAL_STUDENTS:
            st.session_state.today_served += 30
        else:
            st.session_state.today_served = TOTAL_STUDENTS
        st.rerun()

if st.sidebar.button("🔄 오늘 누적 인원 리셋"):
    st.session_state.today_served = 0
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.subheader("2. 좌석 상태 수동 변경")
selected_seat = st.sidebar.selectbox("좌석 선택 (행-열)", df["좌석번호"].tolist())
new_status = st.sidebar.radio("변경할 상태", ["🟢 빈자리", "🔴 식사중"])

if st.sidebar.button("좌석 상태 업데이트"):
    idx = df[df["좌석번호"] == selected_seat].index[0]
    st.session_state.seats_df.loc[idx, "상태"] = new_status
    st.sidebar.success(f"{selected_seat}번 좌석이 [{new_status}] 상태로 변경되었습니다.")
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🎲 실시간 좌석 무작위 갱신"):
    statuses = ["🟢 빈자리", "🔴 식사중", "🔴 식사중"]
    st.session_state.seats_df["상태"] = [random.choice(statuses) for _ in range(len(df))]
    st.rerun()

# 메인 지표 표시 (4개 카드로 단순화)
total_seats = len(df)
empty_seats = len(df[df["상태"] == "🟢 빈자리"])
occupied_seats = len(df[df["상태"] == "🔴 식사중"])
served_rate = round((st.session_state.today_served / TOTAL_STUDENTS) * 100, 1)

m1, m2, m3, m4 = st.columns(4)
m1.metric("급식실 총 좌석", f"{total_seats}석")
m2.metric("🟢 즉시 이용 가능한 빈자리", f"{empty_seats}석")
m3.metric("🔴 현재 식사 중", f"{occupied_seats}석")
m4.metric("👨‍🎓 오늘 식사 진행률", f"{st.session_state.today_served} / {TOTAL_STUDENTS}명", f"{served_rate}% 완료")

st.markdown("---")

# 급식실 좌석 배치도 (시각적 그리드)
st.subheader("📍 급식실 좌석 실시간 배치도 (320석 규모)")
st.caption("⬆️ **위쪽: 배식구 / 식판 수거대 방향**")

# 12시 30분 점심시간 시작 기준 학년별 시차 배식 안내
st.warning("⏰ **점심시간(12:30 시작) 학년별 배식 순서**: 2학년 (12:30~) ➡️ 3학년 (12:50~) ➡️ 1학년 (13:10~)")

# 행별 좌석 출력
for r in range(1, SEAT_ROWS + 1):
    with st.expander(f"📌 {r}구역 라인 좌석 보기 (40석)", expanded=(r <= 2)):
        row_df = df[df["행"] == r].sort_values("열")
        
        # 10개씩 깔끔하게 분할 표시
        for chunk_idx in range(0, SEAT_COLS, 10):
            cols = st.columns(10)
            chunk = row_df.iloc[chunk_idx:chunk_idx+10]
            for idx, (_, seat) in enumerate(chunk.iterrows()):
                with cols[idx]:
                    seat_num = seat["좌석번호"]
                    status = seat["상태"]
                    if "🟢" in status:
                        st.success(f"**{seat_num}**\n\n빈자리")
                    else:
                        st.error(f"**{seat_num}**\n\n식사중")

st.markdown("---")

# 탭 메뉴
tab1, tab2 = st.tabs(["📊 상세 좌석 목록", "❤️ 오성고 조리사님 응원하기"])

with tab1:
    st.subheader("전체 좌석 상태 데이터")
    st.dataframe(df[["좌석번호", "테이블", "상태"]], use_container_width=True)

with tab2:
    st.subheader("👩‍🍳 맛있는 급식을 만들어 주시는 천안오성고 조리사 선생님께")
    message = st.text_input("응원의 한마디를 입력해주세요:")
    if st.button("메시지 전달하기"):
        if message:
            st.balloons()
            st.success("천안오성고 조리사 선생님들께 소중한 응원 메시지가 전달되었습니다! ❤️")
        else:
            st.warning("메시지 내용을 입력해 주세요.")
