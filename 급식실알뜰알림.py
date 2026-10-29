
import calendar
import csv
import io
from datetime import date, datetime, timedelta

import streamlit as st

# ==========================================
# 기본 설정
# ==========================================
st.set_page_config(
    page_title="급식실 알뜰알림",
    page_icon="🍚",
    layout="wide",
)

SCHOOL_NAME = "천안오성고등학교"
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

# 가상 급식 메뉴
LUNCH_MENUS = [
    ("현미밥", "미역국", "제육볶음", "콩나물무침", "배추김치"),
    ("흑미밥", "된장찌개", "간장찜닭", "시금치나물", "깍두기"),
    ("차조밥", "김치찌개", "돈가스", "양배추샐러드", "요구르트"),
    ("보리밥", "순두부찌개", "오리불고기", "숙주나물", "배추김치"),
    ("기장밥", "어묵국", "함박스테이크", "감자조림", "깍두기"),
    ("카레라이스", "유부장국", "새우튀김", "단무지", "배추김치"),
    ("비빔밥", "계란국", "고추장소스", "김가루", "바나나"),
    ("잡곡밥", "육개장", "생선까스", "브로콜리", "배추김치"),
    ("쌀밥", "닭곰탕", "떡갈비", "오이무침", "깍두기"),
    ("김치볶음밥", "콩나물국", "계란후라이", "만두튀김", "단무지"),
]

DINNER_MENUS = [
    ("쌀밥", "얼큰한우국", "닭갈비", "무생채", "배추김치"),
    ("현미밥", "북엇국", "돼지불고기", "두부조림", "깍두기"),
    ("흑미밥", "김치국", "치킨너겟", "콘샐러드", "배추김치"),
    ("보리밥", "감자국", "소불고기", "멸치볶음", "깍두기"),
    ("잡곡밥", "순댓국", "메추리알장조림", "김구이", "배추김치"),
    ("짜장밥", "짬뽕국", "탕수육", "단무지", "요구르트"),
]

# 가상 학사일정: 실제 학교 일정이 아님
EVENTS = {
    1: [(5, "새해 학사 준비"), (20, "겨울방학 중 학교 안내")],
    2: [(2, "개학 준비 기간"), (10, "졸업식 및 종업식 예시")],
    3: [(2, "개학 및 입학식 예시"), (16, "학급 임원 선거 예시")],
    4: [(6, "학교 안전교육 예시"), (20, "진로 탐색 활동 예시")],
    5: [(4, "학교 재량휴업일 예시"), (15, "체육 행사 예시")],
    6: [(10, "모의평가 예시"), (22, "기말고사 준비 예시")],
    7: [(6, "기말고사 예시"), (20, "여름방학식 예시")],
    8: [(17, "개학 예시"), (24, "학생자치 활동 예시")],
    9: [(7, "모의평가 예시"), (21, "진로 체험 예시")],
    10: [(5, "학교 안전교육 예시"), (15, "중간고사 예시"), (23, "동아리 활동 예시")],
    11: [(5, "진로 특강 예시"), (18, "대학수학능력시험일 관련 일정 예시")],
    12: [(7, "기말고사 예시"), (24, "겨울방학식 예시")],
}

# 가상으로 급식이 없는 날짜
# 해당 월의 평일 5일, 16일, 23일에 적용
NO_MEAL_DAYS = {5, 16, 23}

# 가상으로 석식만 없는 날짜
NO_DINNER_DAYS = {8, 12, 19, 26}

# ==========================================
# 디자인
# ==========================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F5F7FB;
    }
    .hero {
        padding: 24px;
        border-radius: 18px;
        background: linear-gradient(120deg, #163B65, #2876A8);
        color: white;
        margin-bottom: 18px;
    }
    .hero h1 {
        font-size: 2.1rem;
        margin: 0;
    }
    .hero p {
        margin-bottom: 0;
        color: #E7F2FF;
    }
    .notice {
        padding: 12px 16px;
        background: #FFF4D6;
        border-radius: 10px;
        border: 1px solid #F3D58A;
        color: #6B4B00;
        margin-bottom: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 가상 데이터 생성
# ==========================================
def get_events(year, month):
    """선택한 달의 가상 학사일정을 생성합니다."""
    result = []

    for day, name in EVENTS.get(month, []):
        try:
            event_date = date(year, month, day)
        except ValueError:
            continue

        result.append({
            "date": event_date,
            "name": name,
        })

    # 매월 마지막 주 금요일에 가상 학급 활동 추가
    last_day = calendar.monthrange(year, month)[1]
    for day in range(last_day, max(0, last_day - 7), -1):
        current = date(year, month, day)
        if current.weekday() == 4:
            result.append({
                "date": current,
                "name": "학급 활동 예시",
            })
            break

    return sorted(result, key=lambda item: item["date"])


def get_meals(year, month):
    """선택한 달의 가상 중식·석식 데이터를 생성합니다."""
    result = []
    last_day = calendar.monthrange(year, month)[1]

    for day in range(1, last_day + 1):
        current = date(year, month, day)

        # 주말에는 급식 데이터를 생성하지 않음
        if current.weekday() >= 5:
            continue

        # 가상 미급식일
        if day in NO_MEAL_DAYS:
            continue

        lunch = LUNCH_MENUS[(day + month) % len(LUNCH_MENUS)]

        result.append({
            "date": current,
            "type": "중식",
            "menu": lunch,
            "calories": 650 + (day * 17 + month * 11) % 250,
        })

        # 가상 석식 미제공일
        if day in NO_DINNER_DAYS:
            continue

        dinner = DINNER_MENUS[(day + month) % len(DINNER_MENUS)]

        result.append({
            "date": current,
            "type": "석식",
            "menu": dinner,
            "calories": 550 + (day * 13 + month * 7) % 250,
        })

    return result


def format_date(day):
    return f"{day.month}월 {day.day}일 ({WEEKDAYS[day.weekday()]})"


def get_day_meals(meals, day):
    return [meal for meal in meals if meal["date"] == day]


def get_day_events(events, day):
    return [event for event in events if event["date"] == day]


def meal_exists(meals, day, meal_type):
    return any(
        meal["date"] == day and meal["type"] == meal_type
        for meal in meals
    )


def make_csv(meals):
    """급식표를 UTF-8 BOM이 포함된 CSV로 변환합니다."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["날짜", "요일", "급식 종류", "메뉴", "열량(kcal)"])

    for meal in meals:
        day = meal["date"]
        writer.writerow([
            day.isoformat(),
            WEEKDAYS[day.weekday()],
            meal["type"],
            " / ".join(meal["menu"]),
            meal["calories"],
        ])

    return output.getvalue().encode("utf-8-sig")


# ==========================================
# 메인 화면
# ==========================================
st.markdown(
    f"""
    <div class="hero">
        <h1>🍚 급식실 알뜰알림</h1>
        <p>{SCHOOL_NAME} · 월별 급식표와 학사일정</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="notice">
        ⚠️ <b>가상 데이터 안내</b><br>
        이 앱의 메뉴, 열량, 학사일정, 미급식 날짜는 시연용 예시입니다.
        실제 학교의 공식 정보가 아니므로 학교 공지를 반드시 확인하세요.
    </div>
    """,
    unsafe_allow_html=True,
)

today = date.today()

with st.sidebar:
    st.title("📅 조회 설정")

    year = st.selectbox(
        "연도",
        list(range(today.year - 1, today.year + 3)),
        index=1,
    )

    month = st.selectbox(
        "월",
        list(range(1, 13)),
        index=today.month - 1,
        format_func=lambda m: f"{m}월",
    )

    st.divider()
    st.caption("데이터 모드: 가상 데이터")
    st.caption("외부 API 및 인증키 불필요")

meals = get_meals(year, month)
events = get_events(year, month)

last_day = calendar.monthrange(year, month)[1]
start_date = date(year, month, 1)
end_date = date(year, month, last_day)

lunch_days = {
    meal["date"] for meal in meals if meal["type"] == "중식"
}
dinner_days = {
    meal["date"] for meal in meals if meal["type"] == "석식"
}

no_lunch_dates = [
    date(year, month, day)
    for day in range(1, last_day + 1)
    if date(year, month, day).weekday() < 5
    and date(year, month, day) not in lunch_days
]

no_dinner_dates = [
    date(year, month, day)
    for day in range(1, last_day + 1)
    if date(year, month, day).weekday() < 5
    and date(year, month, day) not in dinner_days
]

# 상단 요약
st.subheader(f"📊 {year}년 {month}월 한눈에 보기")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("중식 제공일", len(lunch_days))
with c2:
    st.metric("석식 제공일", len(dinner_days))
with c3:
    st.metric("중식 데이터 없음", len(no_lunch_dates))
with c4:
    st.metric("등록된 학사일정", len(events))

# 탭 구성
tab_today, tab_calendar, tab_meal, tab_events, tab_alert = st.tabs([
    "🏠 오늘의 급식",
    "🗓️ 달력",
    "🍱 월별 급식표",
    "📚 학사일정",
    "🔔 미급식 알림",
])

# ==========================================
# 오늘의 급식
# ==========================================
with tab_today:
    st.subheader(f"오늘의 급식 · {format_date(today)}")

    if today.year == year and today.month == month:
        todays_meals = get_day_meals(meals, today)
        todays_events = get_day_events(events, today)

        if todays_meals:
            cols = st.columns(len(todays_meals))

            for col, meal in zip(cols, todays_meals):
                with col:
                    with st.container(border=True):
                        st.markdown(f"### 🍽️ {meal['type']}")
                        for item in meal["menu"]:
                            st.write(f"• {item}")
                        st.caption(f"약 {meal['calories']} kcal")
        else:
            st.info(
                "오늘은 가상 급식 데이터가 없습니다. "
                "실제 급식 여부를 뜻하지는 않습니다."
            )

        st.markdown("### 📌 오늘의 학사일정")

        if todays_events:
            for event in todays_events:
                st.write(f"📍 {event['name']}")
        else:
            st.write("등록된 가상 일정이 없습니다.")
    else:
        st.info(
            f"오늘은 {today.year}년 {today.month}월입니다. "
            "오늘의 급식을 보려면 사이드바에서 현재 월을 선택하세요."
        )

    st.caption("메뉴와 일정은 모두 가상 데이터입니다.")

# ==========================================
# 달력
# ==========================================
with tab_calendar:
    st.subheader(f"🗓️ {year}년 {month}월 달력")

    calendar_rows = calendar.Calendar(
        firstweekday=0
    ).monthdatescalendar(year, month)

    header = st.columns(7)

    for col, weekday in zip(header, WEEKDAYS):
        col.markdown(f"**{weekday}**")

    for week in calendar_rows:
        cols = st.columns(7)

        for col, day in zip(cols, week):
            with col:
                if day.month != month:
                    st.write(" ")
                    continue

                day_meals = get_day_meals(meals, day)
                day_events = get_day_events(events, day)

                with st.container(border=True):
                    st.markdown(f"**{day.day}일**")

                    if day in lunch_days:
                        st.caption("🍚 중식")
                    elif day.weekday() < 5:
                        st.caption("⚠️ 중식 없음")

                    if day in dinner_days:
                        st.caption("🌙 석식")
                    elif day.weekday() < 5:
                        st.caption("⚠️ 석식 없음")

                    for event in day_events:
                        st.caption(f"📌 {event['name']}")

    st.caption(
        "달력은 가상 데이터로 구성됩니다. "
        "급식이 없다고 표시된 날은 실제 휴업일을 의미하지 않습니다."
    )

# ==========================================
# 월별 급식표
# ==========================================
with tab_meal:
    st.subheader(f"🍱 {year}년 {month}월 월별 급식표")

    csv_data = make_csv(meals)

    st.download_button(
        "📥 월별 급식표 CSV 다운로드",
        data=csv_data,
        file_name=f"급식실알뜰알림_{year}_{month:02d}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    selected_day = st.date_input(
        "날짜별 식단 확인",
        value=date(year, month, min(today.day, last_day)),
        min_value=start_date,
        max_value=end_date,
    )

    selected_meals = get_day_meals(meals, selected_day)

    if selected_meals:
        for meal in selected_meals:
            with st.container(border=True):
                st.markdown(f"### {meal['type']}")

                for item in meal["menu"]:
                    st.write(f"• {item}")

                st.caption(f"예시 열량: 약 {meal['calories']} kcal")
    else:
        st.info(
            "이 날짜에는 가상 급식 데이터가 없습니다. "
            "실제 미급식 여부는 학교 공지를 확인하세요."
        )

    st.markdown("### 전체 월간 식단")

    for day_num in range(1, last_day + 1):
        day = date(year, month, day_num)
        day_meals = get_day_meals(meals, day)

        if not day_meals:
            continue

        with st.expander(format_date(day)):
            for meal in day_meals:
                st.markdown(f"**{meal['type']}**")
                st.write(" · ".join(meal["menu"]))
                st.caption(f"약 {meal['calories']} kcal")

# ==========================================
# 학사일정
# ==========================================
with tab_events:
    st.subheader(f"📚 {year}년 {month}월 학사일정")

    if events:
        for event in events:
            with st.container(border=True):
                st.markdown(f"**📅 {format_date(event['date'])}**")
                st.write(event["name"])
                st.caption("가상 학사일정 예시")
    else:
        st.info("이 달에 설정된 가상 학사일정이 없습니다.")

    st.caption(
        "실제 시험일, 방학일, 학교 행사와는 무관한 예시 일정입니다."
    )

# ==========================================
# 미급식 알림
# ==========================================
with tab_alert:
    st.subheader("🔔 급식·석식 없는 날 미리 보기")

    st.write(
        "선택한 달의 평일 중 가상 급식 데이터가 없는 날을 표시합니다."
    )

    if no_lunch_dates:
        st.markdown("### 🍚 중식 데이터가 없는 날")

        for day in no_lunch_dates:
            st.warning(
                f"{format_date(day)} · 중식 데이터 없음 "
                "— 가상 예시"
            )

    if no_dinner_dates:
        st.markdown("### 🌙 석식 데이터가 없는 날")

        for day in no_dinner_dates:
            st.info(
                f"{format_date(day)} · 석식 데이터 없음 "
                "— 가상 예시"
            )

    upcoming = sorted(
        day for day in set(no_lunch_dates + no_dinner_dates)
        if day >= today
    )

    st.markdown("### ⏰ 앞으로 확인할 날짜")

    if upcoming:
        for day in upcoming[:5]:
            missing = []

            if day in no_lunch_dates:
                missing.append("중식")
            if day in no_dinner_dates:
                missing.append("석식")

            st.write(
                f"📅 {format_date(day)}: "
                f"{', '.join(missing)} 데이터 없음"
            )
    else:
        st.info(
            "선택한 달에 오늘 이후의 가상 미급식 날짜가 없습니다."
        )

    st.divider()
    st.caption(
        "이 앱은 실제 푸시 알림을 보내지 않습니다. "
        "화면에 표시되는 가상 일정 및 급식 데이터를 확인하는 기능입니다."
    )

# ==========================================
# 하단
# ==========================================
st.divider()

st.caption(
    "🍚 급식실 알뜰알림 | 천안오성고등학교용 시연 앱 | "
    "모든 메뉴·열량·학사일정은 가상 데이터"
)
