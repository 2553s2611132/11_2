import streamlit as st
import pandas as pd
import numpy as np

### 페이지 기본 설정
st.set_page_config(
    page_title="급식실 좌석 현황판",
    page_icon="🍱",
    layout="wide"
)

### 커스텀 CSS (좌석 버튼 스타일링)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 60px;
        font-weight: bold;
        font-size: 16px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

### --- 세션 상태 초기화 ---
TOTAL_SEATS_PER_ZONE = 12
ZONES = ["A구역", "B구역", "C구역", "D구역"]

if "seats" not in st.session_state:
### False: 빈 좌석, True: 사용 중
    st.session_state.seats = {
        zone: [False] * TOTAL_SEATS_PER_ZONE for zone in ZONES
    }

### --- 헤더 섹션 ---
st.title("🍱 급식실 실시간 좌석 현황판")
st.caption("현재 남은 좌석을 확인하고, 식사 시작/완료 시 좌석을 클릭해 주세요.")

### --- 좌석 현황 요약 (Metrics) ---
total_seats = len(ZONES) * TOTAL_SEATS_PER_ZONE
occupied_seats = sum(sum(zone) for zone in st.session_state.seats.values())
available_seats = total_seats - occupied_seats
occupancy_rate = (occupied_seats / total_seats) * 100

m1, m2, m3, m4 = st.columns(4)
m1.metric("전체 좌석", f"{total_seats}석")
m2.metric("이용 중인 좌석", f"{occupied_seats}석", delta=f"{occupied_seats}명 식사 중", delta_color="inverse")
m3.metric("잔여 좌석", f"{available_seats}석", delta=f"{available_seats}석 이용 가능")
m4.metric("혼잡도", f"{occupancy_rate:.1f}%")

### 혼잡도 프로그레스 바 및 안내 메세지
st.progress(occupancy_rate / 100)
if occupancy_rate >= 80:
    st.error("🚨 현재 급식실이 매우 혼잡합니다! 입장에 시간이 소요될 수 있습니다.")
elif occupancy_rate >= 50:
    st.warning("⚠️ 보통 수준의 혼잡도입니다.")
else:
    st.success("✅ 원활하게 이용 가능합니다.")

st.markdown("---")

### --- 사이드바: 관리자 컨트롤 ---
st.sidebar.header("⚙️ 급식실 관리 메뉴")

### 임의 데이터 채우기 (테스트용)
if st.sidebar.button("🎲 랜덤으로 좌석 채우기 (테스트)"):
    for zone in ZONES:
        st.session_state.seats[zone] = [np.random.choice([True, False], p=[0.4, 0.6]) for _ in range(TOTAL_SEATS_PER_ZONE)]
    st.rerun()

### 전체 초기화
if st.sidebar.button("🔄 전체 좌석 리셋 (퇴실 처리)"):
    for zone in ZONES:
        st.session_state.seats[zone] = [False] * TOTAL_SEATS_PER_ZONE
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📌 범례")
st.sidebar.markdown("🟩 **이용 가능**: 클릭 시 입실 처리")
st.sidebar.markdown("🟥 **이용 중**: 클릭 시 퇴실 처리")

### --- 메인: 좌석 배치도 (4개 구역) ---
st.subheader("🗺️ 구역별 좌석 배치도")

cols = st.columns(4)

for idx, zone in enumerate(ZONES):
    with cols[idx]:
        zone_occupied = sum(st.session_state.seats[zone])
        st.markdown(f"### {zone} (`{TOTAL_SEATS_PER_ZONE - zone_occupied}/{TOTAL_SEATS_PER_ZONE}`석 가능)")
        
### 3열로 좌석 배치
        seat_cols = st.columns(3)
        for seat_idx in range(TOTAL_SEATS_PER_ZONE):
            col_target = seat_cols[seat_idx % 3]
            is_occupied = st.session_state.seats[zone][seat_idx]
            
            seat_num = f"{seat_idx + 1:02d}"
            label = f"🟥 {seat_num} (사용중)" if is_occupied else f"🟩 {seat_num} (빈좌석)"
            
            if col_target.button(label, key=f"{zone}_{seat_idx}"):
                st.session_state.seats[zone][seat_idx] = not is_occupied
                st.rerun()
