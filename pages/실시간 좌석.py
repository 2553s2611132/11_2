import streamlit as st
import pandas as pd
import plotly.express as px
import random
import time

# ----------------------------------------------------
# 1. 페이지 기본 설정 및 디자인 스타일링
# ----------------------------------------------------
st.set_page_config(
    page_title="급식실 실시간 좌석 현황판",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 메인 커스텀 스타일 적용 (급식 아주머니/조리사님을 위한 따뜻하고 가독성 높은 디자인)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #FF9A9E 0%, #FECFEF 99%, #FECFEF 100%);
        padding: 20px;
        border-radius: 15px;
        color: #333333;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card {
        background-color: #ffffff;
        border: 2px solid #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .seat-legend {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-bottom: 15px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. 데이터 세션 상태 관리 (앱 실행 중 상태 유지)
# ----------------------------------------------------
def init_seats(rows=6, cols=10):
    """초기 좌석 배치 데이터 생성 (6행 10열 = 총 60석)"""
    seats = []
    # 미리 일정한 비율로 빈자리/사용중 지정
    random.seed(42)  # 초깃값 고정
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            # 행에 따라 구역(테이블) 나누기
            zone = f"테이블 {((r-1)//2) + 1}"
            status = random.choice(["사용중", "사용중", "빈자리"])
            seats.append({
                "행": r,
                "열": c,
                "좌석번호": f"{r}행-{c}열",
                "구역": zone,
                "상태": status
            })
    return pd.DataFrame(seats)

if "seat_data" not in st.session_state:
    st.session_state.seat_data = init_seats()

if "total_served" not in st.session_state:
    st.session_state.total_served = 142  # 오늘 누적 식사 인원 초기값

# ----------------------------------------------------
# 3. 사이드바: 급식 아주머니/관리자 전용 제어판
# ----------------------------------------------------
st.sidebar.image("https://img.icons8.com/emoji/96/000000/bento-box-emoji.png", width=70)
st.sidebar.title("👩‍🍳 급식 관리자 제어판")
st.sidebar.caption("식사를 준비해 주시는 조리사/관리자 전용 기능입니다.")

st.sidebar.markdown("---")

# 기능 A: 실시간 식수(누적 인원) 추가
st.sidebar.subheader("➕ 오늘 누적 식사자 카운트")
col_add1, col_add2 = st.sidebar.columns(2)
with col_add1:
    if st.button("🙋‍♂️ +1명 입실"):
        st.session_state.total_served += 1
        st.toast("누적 식사 인원이 +1명 증가했습니다!", icon="🍽️")
with col_add2:
    if st.button("🔄 리셋", help="누적 인원 리셋"):
        st.session_state.total_served = 0
        st.toast("오늘 누적 식사 인원이 리셋되었습니다.")

st.sidebar.markdown("---")

# 기능 B: 특정 좌석 수동 상태 변경 (퇴실 조치/소독 필요 등)
st.sidebar.subheader("🪑 특정 좌석 상태 변경")
selected_seat = st.sidebar.selectbox(
    "좌석 선택",
    options=st.session_state.seat_data["좌석번호"].tolist()
)
new_status = st.sidebar.radio("변경할 상태 선택", ["빈자리", "사용중", "점검중"])

if st.sidebar.button("좌석 상태 업데이트"):
    idx = st.session_state.seat_data[st.session_state.seat_data["좌석번호"] == selected_seat].index[0]
    st.session_state.seat_data.loc[idx, "상태"] = new_status
    st.toast(f"{selected_seat} 좌석이 [{new_status}] 상태로 변경되었습니다.", icon="✅")

st.sidebar.markdown("---")

# 기능 C: 현황 초기화 및 시뮬레이션
if st.sidebar.button("🎲 실시간 현황 랜덤 갱신 (시뮬레이션)"):
    statuses = ["빈자리", "사용중", "사용중", "점검중"]
    weights = [0.4, 0.5, 0.05, 0.05]
    st.session_state.seat_data["상태"] = [
        random.choices(statuses, weights=weights)[0] 
        for _ in range(len(st.session_state.seat_data))
    ]
    st.rerun()

# ----------------------------------------------------
# 4. 메인 화면 구성
# ----------------------------------------------------

# 메인 타이틀
st.markdown("""
<div class="main-header">
    <h1>🍱 급식실 실시간 좌석 현황판</h1>
    <p style="font-size: 1.1em; margin-bottom: 0px;">
        맛있는 식사를 준비해주시는 급식 아주머니와 함께하는 쾌적한 급식실 이용 현황
    </p>
</div>
""", unsafe_allow_html=True)

# 4-1. 주요 지표 요약 (Metric Cards)
df = st.session_state.seat_data
total_seats = len(df)
occupied_seats = len(df[df["상태"] == "사용중"])
empty_seats = len(df[df["상태"] == "빈자리"])
maintenance_seats = len(df[df["상태"] == "점검중"])
occupancy_rate = int((occupied_seats / total_seats) * 100) if total_seats > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(label="총 좌석 수", value=f"{total_seats}석")
with col2:
    st.metric(label="🟢 이용 가능한 빈자리", value=f"{empty_seats}석", delta=f"{empty_seats}석 남음")
with col3:
    st.metric(label="🔴 현재 식사 중", value=f"{occupied_seats}석")
with col4:
    st.metric(label="📊 혼잡도", value=f"{occupancy_rate}%")
with col5:
    st.metric(label="👨‍👩‍👧‍👦 오늘 총 식사 인원", value=f"{st.session_state.total_served}명")

st.markdown("---")

# 4-2. 급식실 좌석 배치도 시각화
st.subheader("📍 급식실 좌석 배치도 (실시간)")
st.caption("배치도 상의 각 셀은 좌석 위치를 나타냅니다. (위쪽: 배식대 / 아래쪽: 퇴식구)")

# 범례 안내
st.markdown("""
<div class="seat-legend">
    <span style="color:#2ecc71;">🟢 빈자리 (식사 가능)</span> | 
    <span style="color:#e74c3c;">🔴 사용중 (식사 중)</span> | 
    <span style="color:#95a5a6;">⚪ 점검중 (소독/정리 필요)</span>
</div>
""", unsafe_allow_html=True)

try:
    # Plotly Heatmap/Scatter 형태의 좌석 지도 시각화
    color_map = {"빈자리": "#2ecc71", "사용중": "#e74c3c", "점검중": "#95a5a6"}
    
    fig = px.scatter(
        df,
        x="열",
        y="행",
        color="상태",
        symbol="상태",
        color_discrete_map=color_map,
        hover_name="좌석번호",
        hover_data={"구역": True, "행": False, "열": False, "상태": True},
        size_max=35
    )
    
    fig.update_traces(marker=dict(size=32, line=dict(width=2, color='DarkSlateGrey')))
    
    # Y축 반전 (1행이 맨 위에 오도록)
    fig.update_layout(
        yaxis=dict(autorange="reversed", title="행 (배식대 방향 ⬆️)", tickmode='linear'),
        xaxis=dict(title="열", tickmode='linear'),
        height=450,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"좌석 시각화 중 오류가 발생했습니다: {e}")

# 4-3. 하단 탭 (구역별 세부 현황 & 급식실 정보)
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["🔍 구역별 빈자리 검색", "📋 전체 좌석 리스트", "❤️ 급식실 응원 한마디"])

with tab1:
    st.subheader("테이블 구역별 잔여 좌석")
    zone_summary = df.groupby(["구역", "상태"]).size().unstack(fill_value=0)
    
    # 빈자리 컬럼이 없을 경우를 대비한 예외 처리
    if "빈자리" not in zone_summary.columns:
        zone_summary["빈자리"] = 0
    if "사용중" not in zone_summary.columns:
        zone_summary["사용중"] = 0
        
    zone_summary["총 좌석"] = zone_summary.sum(axis=1)
    zone_summary["혼잡도(%)"] = ((zone_summary["사용중"] / zone_summary["총 좌석"]) * 100).round(1)
    
    st.dataframe(zone_summary[["총 좌석", "빈자리", "사용중", "혼잡도(%)"]], use_container_width=True)

with tab2:
    st.subheader("전체 좌석 데이터 목록")
    filter_status = st.multiselect("상태 필터링", options=["빈자리", "사용중", "점검중"], default=["빈자리"])
    filtered_df = df[df["상태"].isin(filter_status)]
    st.dataframe(filtered_df, use_container_width=True)

with tab3:
    st.subheader("👩‍🍳 식사를 준비해 주시는 조리사님께 전하는 응원 메시지")
    cheer_msg = st.text_input("따뜻한 한마디를 남겨주세요!", placeholder="오늘도 맛있는 급식 감사히 잘 먹겠습니다!")
    if st.button("메시지 보내기"):
        if cheer_msg:
            st.success("❤️ 응원 메시지가 전송되었습니다! 조리사님들께 큰 힘이 됩니다.")
        else:
            st.warning("메시지를 입력해 주세요.")
