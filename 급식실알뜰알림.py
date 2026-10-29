
import calendar
import csv
import io
from datetime import date, timedelta

import streamlit as st


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="급식실 알뜰알림",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCHOOL_NAME = "천안오성고등학교"

# 가상 급식 데이터: 실제 학교 급식표가 아님
LUNCH_MENUS = [
    "쌀밥, 김치찌개, 돈육볶음, 계란말이, 깍두기",
    "현미밥, 된장찌개, 닭갈비, 콩나물무침, 배추김치",
    "흑미밥, 미역국, 간장불고기, 감자채볶음, 배추김치",
    "보리밥, 순두부찌개, 생선까스, 양배추샐러드, 깍두기",
    "카레라이스, 유부장국, 군만두, 단무지, 배추김치",
    "쌀밥, 소고기뭇국, 제육볶음, 시금치나물, 배추김치",
    "콩나물밥, 어묵국, 떡갈비, 오이무침, 깍두기",
    "잡곡밥, 닭곰탕, 두부조림, 멸치볶음, 배추김치",
]

DINNER_MENUS = [
    "쌀밥, 육개장, 미트볼조림, 배추김치",
    "현미밥, 김치국, 돈까스, 양배추샐러드",
    "흑미밥, 어묵국, 닭볶음, 깍두기",
    "보리밥, 부대찌개, 계란찜, 배추김치",
    "짜장밥, 계란국, 탕수육, 단무지",
    "쌀밥, 순댓국, 부추무침, 깍두기",
    "잡곡밥, 된장찌개, 고등어구이, 배추김치",
    "카레라이스, 미소장국, 핫도그, 배추김치",
]

# 가상 학사일정: 실제 천안오성고등학교 공식 일정이 아님
EVENTS = {
    1: [
        (5, "겨울방학 학습 안내"),
        (8, "자기주도학습 안내"),
        (15, "신입생 예비 안내"),
        (20, "교직원 연수 예시"),
        (26, "새 학년도 교육과정 준비"),
    ],
    2: [
        (3, "신입생 학교생활 안내"),
        (6, "졸업식 예시"),
        (9, "종업식 예시"),
        (12, "새 학년도 준비"),
        (23, "신입생 오리엔테이션 예시"),
        (27, "교실 환경 정비"),
    ],
    3: [
        (2, "개학 및 입학식 예시"),
        (4, "학교생활 안내 교육"),
        (9, "학급 임원 선거"),
        (13, "학생 안전교육"),
        (18, "동아리 신청"),
        (23, "학부모 상담 주간 시작"),
        (27, "학부모 상담 주간 종료"),
        (31, "진로 탐색 활동"),
    ],
    4: [
        (3, "학교폭력 예방교육"),
        (8, "학생 건강교육"),
        (10, "과학의 날 행사 예시"),
        (14, "중간고사 예시"),
        (15, "중간고사 예시"),
        (16, "중간고사 예시"),
        (20, "장애 이해교육"),
        (24, "진로 체험 활동"),
        (29, "학생 자치회"),
    ],
    5: [
        (1, "학교 일정 확인일"),
        (4, "가상 재량휴업일"),
        (8, "어버이날 감사 활동"),
        (12, "체육대회 준비"),
        (15, "교내 체육대회 예시"),
        (18, "민주시민교육"),
        (20, "동아리 발표 활동"),
        (25, "진로 특강"),
        (29, "학교 환경 정리"),
    ],
    6: [
        (3, "모의평가 예시"),
        (5, "환경교육 활동"),
        (9, "학생 인권교육"),
        (12, "기말고사 준비 안내"),
        (17, "기말고사 예시"),
        (18, "기말고사 예시"),
        (19, "기말고사 예시"),
        (23, "진로 상담"),
        (26, "동아리 활동"),
        (30, "여름방학 생활 안내"),
    ],
    7: [
        (3, "기말고사 예시"),
        (7, "성적 확인 및 상담"),
        (10, "학생 자치 활동"),
        (15, "여름방학 안전교육"),
        (17, "여름방학식 예시"),
        (20, "여름방학 안내"),
        (27, "방학 중 도서관 이용 안내"),
    ],
    8: [
        (3, "여름방학 진로 탐색"),
        (10, "2학기 준비 안내"),
        (14, "광복절 관련 안내"),
        (17, "2학기 개학 예시"),
        (19, "학급 임원 선거"),
        (21, "동아리 활동 재개"),
        (26, "학생 안전교육"),
        (31, "학부모 상담 안내"),
    ],
    9: [
        (2, "모의평가 예시"),
        (4, "학교폭력 예방교육"),
        (9, "진로 탐색 주간 시작"),
        (11, "진로 탐색 주간 종료"),
        (14, "학생 자치회"),
        (18, "동아리 발표 준비"),
        (22, "학교 독서 행사"),
        (25, "학급별 진로 활동"),
        (30, "중간고사 준비 안내"),
    ],
    10: [
        (5, "학교 안전교육"),
        (8, "한글날 관련 안내"),
        (12, "중간고사 예시"),
        (13, "중간고사 예시"),
        (14, "중간고사 예시"),
        (16, "시험 후 학습 상담"),
        (20, "진로 특강"),
        (23, "동아리 발표회 예시"),
        (27, "학생 인권교육"),
        (30, "학교 환경 캠페인"),
    ],
    11: [
        (3, "학생 자치 활동"),
        (6, "진로 탐색 프로그램"),
        (11, "대학 진학 정보 안내"),
        (18, "대학수학능력시험 관련 일정 예시"),
        (20, "진학 상담 주간 시작"),
        (24, "진학 상담 주간 종료"),
        (26, "동아리 활동"),
        (30, "겨울철 안전교육"),
    ],
    12: [
        (2, "기말고사 준비"),
        (7, "기말고사 예시"),
        (8, "기말고사 예시"),
        (9, "기말고사 예시"),
        (11, "성적 확인 및 상담"),
        (16, "학생회 활동"),
        (18, "학생 작품 발표회 예시"),
        (22, "겨울방학 안전교육"),
        (24, "겨울방학식 예시"),
        (28, "겨울방학 중 학교 안내"),
    ],
}

# 가상 급식 미운영일
# 월: {일: 사유}
NO_MEAL_DAYS = {
    1: {1: "신정 예시", 6: "방학 중 급식 미운영 예시"},
    2: {6: "졸업식 관련 급식 미운영 예시", 9: "종업식 관련 급식 미운영 예시"},
    3: {2: "개학일 급식 운영 확인 필요"},
    4: {14: "시험 기간 석식 미운영 예시", 15: "시험 기간 석식 미운영 예시"},
    5: {4: "가상 재량휴업일", 15: "체육대회 급식 운영 확인 필요"},
    6: {17: "시험 기간 석식 미운영 예시", 18: "시험 기간 석식 미운영 예시"},
    7: {17: "방학식 급식 운영 확인 필요"},
    8: {17: "개학일 급식 운영 확인 필요"},
    9: {2: "모의평가일 급식 운영 확인 필요"},
    10: {12: "시험 기간 석식 미운영 예시", 13: "시험 기간 석식 미운영 예시"},
    11: {18: "수능 관련 급식 운영 확인 필요"},
    12: {24: "방학식 급식 운영 확인 필요"},
}

WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]


# -----------------------------
# 데이터 처리
# -----------------------------
def get_event_names(month, day):
    return [
        name
        for event_day, name in EVENTS.get(month, [])
        if event_day == day
    ]


def get_meals(target_date):
    # 주말은 가상 급식 미운영일로 처리
    if target_date.weekday() >= 5:
        return None, None, "주말이라 급식이 없는 것으로 설정됨"

    reason = NO_MEAL_DAYS.get(target_date.month, {}).get(target_date.day)

    if reason:
        # 사유에 따라 점심과 석식을 구분하는 간단한 가상 규칙
        if "석식" in reason:
            lunch = LUNCH_MENUS[(target_date.day - 1) % len(LUNCH_MENUS)]
            return lunch, None, reason

        return None, None, reason

    index = (
        target_date.day
        + target_date.month
        + target_date.weekday()
    ) % len(LUNCH_MENUS)

    lunch = LUNCH_MENUS[index]
    dinner = DINNER_MENUS[(index + target_date.day) % len(DINNER_MENUS)]

    return lunch, dinner, ""


def build_month_data(year, month):
    _, last_day = calendar.monthrange(year, month)
    rows = []

    for day in range(1, last_day + 1):
        current = date(year, month, day)
        lunch, dinner, reason = get_meals(current)
        events = get_event_names(month, day)

        rows.append({
            "date": current,
            "weekday": WEEKDAYS_KO[current.weekday()],
            "lunch": lunch or "급식 없음",
            "dinner": dinner or "석식 없음",
            "reason": reason,
            "events": ", ".join(events) if events else "",
        })

    return rows


def make_csv(rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "날짜", "요일", "점심", "석식", "급식 안내", "학사일정"
    ])

    for row in rows:
        writer.writerow([
            row["date"].isoformat(),
            row["weekday"],
            row["lunch"],
            row["dinner"],
            row["reason"],
            row["events"],
        ])

    return output.getvalue().encode("utf-8-sig")


# -----------------------------
# 화면 디자인
# -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f5f7fb;
    }
    .main-title {
        font-size: 2.35rem;
        font-weight: 800;
        color: #173b70;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #63738a;
        font-size: 1rem;
        margin-bottom: 1.2rem;
    }
    .notice {
        background: #fff4d6;
        border-left: 5px solid #f0b429;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 12px 0;
        color: #493b17;
    }
    .calendar-cell {
        background: white;
        border: 1px solid #e1e7f0;
        border-radius: 8px;
        padding: 7px;
        min-height: 112px;
        margin-bottom: 6px;
        overflow-wrap: anywhere;
    }
    .calendar-day {
        font-weight: 800;
        color: #173b70;
        font-size: 1rem;
        margin-bottom: 5px;
    }
    .calendar-small {
        font-size: 0.75rem;
        color: #526176;
        margin-top: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-title">🍱 급식실 알뜰알림</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="sub-title">{SCHOOL_NAME} · 월별 급식표와 학사일정 확인</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="notice">
    ⚠️ <b>가상 데이터 안내</b><br>
    이 앱은 기능 시연용 예시입니다. 급식 메뉴와 학사일정은 실제 학교의 공식 정보가 아닙니다.
    중요한 일정과 급식 여부는 학교의 공식 안내를 확인하세요.
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# 사이드바
# -----------------------------
today = date.today()

with st.sidebar:
    st.header("🔎 조회 설정")

    selected_year = st.selectbox(
        "연도",
        options=list(range(today.year - 1, today.year + 3)),
        index=1,
    )

    selected_month = st.selectbox(
        "월",
        options=list(range(1, 13)),
        index=today.month - 1,
        format_func=lambda m: f"{m}월",
    )

    st.divider()
    st.caption("급식실 알뜰알림")
    st.caption("가상 데이터 기반 학교생활 안내 앱")


rows = build_month_data(selected_year, selected_month)

# 선택한 달의 급식 없는 날 및 일정
no_meal_rows = [
    row for row in rows
    if row["lunch"] == "급식 없음" or row["dinner"] == "석식 없음"
]

event_rows = [row for row in rows if row["events"]]

upcoming_rows = [
    row for row in rows
    if row["date"] >= today and (row["reason"] or row["events"])
][:8]


# -----------------------------
# 메인 요약
# -----------------------------
st.subheader(f"📌 {selected_year}년 {selected_month}월 한눈에 보기")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("이번 달 날짜", f"{len(rows)}일")

with col2:
    st.metric("급식 미운영 표시", f"{len(no_meal_rows)}일")

with col3:
    st.metric("등록된 학사일정", f"{len(event_rows)}건")


# -----------------------------
# 탭 구성
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🍚 월별 급식표",
    "📅 학사일정",
    "🔔 급식 알림",
    "⬇️ 다운로드",
])


with tab1:
    st.subheader(f"{selected_month}월 점심·석식 메뉴")

    for row in rows:
        with st.container(border=True):
            weekday_label = row["weekday"]
            st.markdown(
                f"**{row['date'].month}월 {row['date'].day}일 "
                f"({weekday_label})**"
            )

            left, right = st.columns(2)

            with left:
                st.markdown("**🍚 점심**")
                st.write(row["lunch"])

            with right:
                st.markdown("**🌙 석식**")
                st.write(row["dinner"])

            if row["reason"]:
                st.caption(f"ℹ️ {row['reason']}")

            if row["events"]:
                st.caption(f"📌 학사일정: {row['events']}")


with tab2:
    st.subheader(f"📅 {selected_year}년 {selected_month}월 달력")

    # 요일 제목
    header_cols = st.columns(7)
    for i, weekday in enumerate(WEEKDAYS_KO):
        with header_cols[i]:
            st.markdown(f"**{weekday}**")

    month_calendar = calendar.monthcalendar(selected_year, selected_month)

    for week in month_calendar:
        cols = st.columns(7)

        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown(
                        '<div class="calendar-cell"></div>',
                        unsafe_allow_html=True,
                    )
                    continue

                current_date = date(selected_year, selected_month, day)
                lunch, dinner, reason = get_meals(current_date)
                day_events = get_event_names(selected_month, day)

                if reason:
                    meal_label = "🚫 급식 없음"
                else:
                    meal_label = "🍱 급식 예정"

                html = (
                    f'<div class="calendar-cell">'
                    f'<div class="calendar-day">{day}일</div>'
                    f'<div class="calendar-small">{meal_label}</div>'
                )

                if day_events:
                    for event in day_events[:2]:
                        html += (
                            f'<div class="calendar-small">📌 {event}</div>'
                        )

                    if len(day_events) > 2:
                        html += (
                            f'<div class="calendar-small">외 '
                            f'{len(day_events) - 2}건</div>'
                        )

                if reason:
                    html += (
                        f'<div class="calendar-small">ℹ️ {reason}</div>'
                    )

                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

    st.divider()
    st.subheader("📝 이번 달 학사일정 목록")

    if event_rows:
        for row in event_rows:
            st.write(
                f"- **{row['date'].month}월 {row['date'].day}일 "
                f"({row['weekday']})** — {row['events']}"
            )
    else:
        st.info("선택한 달에 등록된 학사일정이 없습니다.")


with tab3:
    st.subheader("🔔 급식 미운영 안내")

    if no_meal_rows:
        st.caption(
            "아래 날짜는 예시 데이터에 따라 급식이 없거나 "
            "운영 여부 확인이 필요한 날입니다."
        )

        for row in no_meal_rows:
            with st.container(border=True):
                st.markdown(
                    f"**{row['date'].month}월 {row['date'].day}일 "
                    f"({row['weekday']})**"
                )
                st.write(f"점심: {row['lunch']}")
                st.write(f"석식: {row['dinner']}")

                if row["reason"]:
                    st.caption(row["reason"])
    else:
        st.success("선택한 달에 표시된 급식 미운영일이 없습니다.")

    st.divider()
    st.subheader("📌 다가오는 학사일정 및 급식 안내")

    if upcoming_rows:
        for row in upcoming_rows:
            st.write(
                f"- **{row['date'].strftime('%m월 %d일')} "
                f"({row['weekday']})**"
            )

            if row["events"]:
                st.write(f"  - 학사일정: {row['events']}")

            if row["reason"]:
                st.write(f"  - 급식 안내: {row['reason']}")
    else:
        st.info(
            "선택한 달에 오늘 이후로 표시할 일정이 없습니다. "
            "다른 달을 선택해 보세요."
        )

    st.caption(
        "이 버전은 웹 푸시 알림이나 자동 문자 발송을 하지 않습니다. "
        "앱에서 일정을 확인하는 방식입니다."
    )


with tab4:
    st.subheader("⬇️ 월별 급식표 저장")

    st.write(
        "선택한 달의 점심, 석식, 급식 안내 및 학사일정을 "
        "CSV 파일로 저장할 수 있습니다."
    )

    csv_data = make_csv(rows)

    st.download_button(
        label="📥 월별 급식표 CSV 다운로드",
        data=csv_data,
        file_name=f"급식실_알뜰알림_{selected_year}_{selected_month:02d}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.caption(
        "CSV 파일은 엑셀이나 스프레드시트에서 열 수 있습니다."
    )


# -----------------------------
# 하단 안내
# -----------------------------
st.divider()

st.caption(
    "급식실 알뜰알림 | 학교생활을 편리하게 확인하기 위한 시연용 앱"
)
st.caption(
    "주의: 가상 메뉴와 일정은 실제 천안오성고등학교의 "
    "공식 급식표 또는 학사일정이 아닙니다."
)
