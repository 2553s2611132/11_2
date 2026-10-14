import calendar
from datetime import date, datetime
from html import escape

import requests
import streamlit as st

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="급식식 알뜰알림",
    page_icon="🍀",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_URL = "https://open.neis.go.kr/hub"
REGIONS = {
    "서울특별시": "B10",
    "부산광역시": "C10",
    "대구광역시": "D10",
    "인천광역시": "E10",
    "광주광역시": "F10",
    "대전광역시": "G10",
    "울산광역시": "H10",
    "세종특별자치시": "I10",
    "경기도": "J10",
    "강원특별자치도": "K10",
    "충청북도": "M10",
    "충청남도": "N10",
    "전북특별자치도": "P10",
    "전라남도": "Q10",
    "경상북도": "R10",
    "경상남도": "S10",
    "제주특별자치도": "T10",
}

# --------------------------------------------------
# 디자인
# --------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    .stApp {
        background: #F7F9F6;
    }
    [data-testid="stSidebar"] {
        background: #EDF4EC;
    }
    .hero {
        background: #174B37;
        padding: 32px;
        border-radius: 22px;
        color: white;
        margin-bottom: 22px;
    }
    .hero-label {
        font-size: 13px;
        color: #D0E8D7;
        font-weight: 600;
        letter-spacing: 1px;
    }
    .hero h1 {
        font-size: clamp(27px, 4vw, 42px);
        line-height: 1.3;
        margin: 10px 0;
        color: white;
    }
    .hero p {
        color: #E0EEE4;
        margin-bottom: 0;
    }
    .panel {
        background: white;
        border: 1px solid #E5EBE4;
        border-radius: 17px;
        padding: 20px;
        margin-bottom: 14px;
    }
    .panel h3 {
        color: #174B37;
        margin-top: 0;
    }
    .muted {
        color: #68766D;
        font-size: 13px;
    }
    .menu-text {
        line-height: 1.9;
        white-space: pre-line;
    }
    .day-tag {
        display: inline-block;
        background: #E5F3E8;
        color: #205E3E;
        padding: 4px 9px;
        border-radius: 7px;
        font-size: 12px;
        font-weight: 700;
    }
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #E5EBE4;
        padding: 15px;
        border-radius: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# 나이스 API 공통 처리
# --------------------------------------------------
def api_get(endpoint, api_key, params):
    """나이스 API 요청 및 응답 오류 처리."""
    request_params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 1000,
        **params,
    }

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=request_params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        raise RuntimeError("서버 응답 시간이 초과됐어요. 잠시 후 다시 시도해 주세요.")
    except requests.exceptions.RequestException:
        raise RuntimeError("나이스 서버에 연결할 수 없어요. 인터넷 연결을 확인해 주세요.")
    except ValueError:
        raise RuntimeError("서버 응답을 읽을 수 없어요. 잠시 후 다시 시도해 주세요.")

    if not isinstance(data, dict):
        raise RuntimeError("예상하지 못한 서버 응답입니다.")

    # 나이스 API 오류 확인
    if "RESULT" in data:
        result = data["RESULT"]
        code = result.get("CODE", "")
        message = result.get("MESSAGE", "알 수 없는 API 오류")

        # 정상적으로 데이터가 없을 때 발생할 수 있는 코드
        if code == "INFO-200":
            return []

        raise RuntimeError(f"나이스 API 오류 ({code}): {message}")

    return data


def get_rows(data, key):
    """나이스 JSON 응답에서 데이터 행 추출."""
    section = data.get(key)

    if not section:
        return []

    for block in section:
        if isinstance(block, dict) and "row" in block:
            rows = block.get("row", [])
            return rows if isinstance(rows, list) else []

    return []


def find_school(api_key, region_code, school_name):
    data = api_get(
        "schoolInfo",
        api_key,
        {
            "ATPT_OFCDC_SC_CODE": region_code,
            "SCHUL_NM": school_name.strip(),
        },
    )
    return get_rows(data, "schoolInfo")


def get_meals(api_key, school, start, end):
    data = api_get(
        "mealServiceDietInfo",
        api_key,
        {
            "ATPT_OFCDC_SC_CODE": school["ATPT_OFCDC_SC_CODE"],
            "SD_SCHUL_CODE": school["SD_SCHUL_CODE"],
            "MLSV_FROM_YMD": start.strftime("%Y%m%d"),
            "MLSV_TO_YMD": end.strftime("%Y%m%d"),
        },
    )
    return get_rows(data, "mealServiceDietInfo")


def get_schedules(api_key, school, start, end):
    data = api_get(
        "SchoolSchedule",
        api_key,
        {
            "ATPT_OFCDC_SC_CODE": school["ATPT_OFCDC_SC_CODE"],
            "SD_SCHUL_CODE": school["SD_SCHUL_CODE"],
            "AA_FROM_YMD": start.strftime("%Y%m%d"),
            "AA_TO_YMD": end.strftime("%Y%m%d"),
        },
    )
    return get_rows(data, "SchoolSchedule")


# --------------------------------------------------
# 화면 상단
# --------------------------------------------------
today = date.today()

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-label">YOUR SCHOOL, AT A GLANCE</div>
        <h1>🍀 급식식 알뜰알림</h1>
        <p>오늘의 메뉴부터 학교 일정까지, 한눈에 확인해요.</p>
        <p style="margin-top:16px;font-size:13px;">
            {today.strftime("%Y년 %m월 %d일")}
            &nbsp; · &nbsp; 매일의 학교생활을 더 간편하게
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# 학교 설정
# --------------------------------------------------
with st.sidebar:
    st.markdown("## 🏫 학교 설정")
    st.caption("학교를 선택하면 해당 학교의 정보를 조회해요.")

    api_key = st.secrets.get("NEIS_API_KEY", "")

    region = st.selectbox(
        "시·도 교육청",
        list(REGIONS.keys()),
        index=list(REGIONS.keys()).index("서울특별시"),
    )

    school_name = st.text_input(
        "학교명",
        placeholder="예: 서울고등학교",
    )

    search_clicked = st.button(
        "학교 검색",
        type="primary",
        use_container_width=True,
    )

    if not api_key:
        st.warning(
            "먼저 Streamlit Secrets에 NEIS_API_KEY를 설정해 주세요."
        )

    if search_clicked:
        if not api_key:
            st.error("나이스 API 인증키가 필요해요.")
        elif not school_name.strip():
            st.warning("학교명을 입력해 주세요.")
        else:
            with st.spinner("학교를 검색하고 있어요..."):
                try:
                    found = find_school(
                        api_key,
                        REGIONS[region],
                        school_name,
                    )
                    st.session_state["school_results"] = found
                    st.session_state["school_region"] = region

                    if not found:
                        st.info("검색 결과가 없어요. 학교명을 확인해 주세요.")

                except RuntimeError as exc:
                    st.error(str(exc))

    results = st.session_state.get("school_results", [])

    selected_school = None
    if results:
        options = [
            (
                f'{row.get("SCHUL_NM", "학교명 없음")} · '
                f'{row.get("LCTN_SC_NM", region)} · '
                f'{row.get("SCHUL_KND_SC_NM", "학교")}'
            )
            for row in results
        ]

        selected_index = st.selectbox(
            "검색 결과에서 학교 선택",
            range(len(options)),
            format_func=lambda i: options[i],
            key="school_choice",
        )

        if st.button("이 학교로 설정", use_container_width=True):
            st.session_state["selected_school"] = results[selected_index]
            st.rerun()

    if st.session_state.get("selected_school"):
        current_school = st.session_state["selected_school"]
        st.success(f'선택된 학교: {current_school.get("SCHUL_NM", "")}')
    else:
        current_school = None
        st.info("학교를 검색한 후 선택해 주세요.")

    st.divider()
    st.caption("데이터 출처: 교육부 나이스 교육정보 개방 포털")


# --------------------------------------------------
# 월 선택
# --------------------------------------------------
st.markdown("### 📅 월별 급식 & 학사일정")

c1, c2 = st.columns([1, 2])

with c1:
    selected_year = st.selectbox(
        "연도",
        range(today.year - 1, today.year + 3),
        index=1,
    )

with c2:
    selected_month = st.selectbox(
        "월",
        list(range(1, 13)),
        index=today.month - 1,
        format_func=lambda m: f"{m}월",
    )

last_day = calendar.monthrange(selected_year, selected_month)[1]
month_start = date(selected_year, selected_month, 1)
month_end = date(selected_year, selected_month, last_day)

if not current_school:
    st.markdown(
        """
        <div class="panel">
            <h3>반가워요! 👋</h3>
            <p>왼쪽에서 학교를 검색하고 선택하면 시작할 수 있어요.</p>
            <p class="muted">
                월별 중식·석식, 학사일정, 급식 정보가 없는 날짜를
                한 페이지에서 확인할 수 있어요.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# --------------------------------------------------
# 데이터 불러오기
# --------------------------------------------------
with st.spinner(f"{selected_month}월 학교 정보를 불러오는 중..."):
    try:
        meals = get_meals(
            api_key,
            current_school,
            month_start,
            month_end,
        )
        schedules = get_schedules(
            api_key,
            current_school,
            month_start,
            month_end,
        )
        load_error = None

    except RuntimeError as exc:
        meals = []
        schedules = []
        load_error = str(exc)

if load_error:
    st.error(load_error)
    st.info("잠시 후 다시 시도하거나 학교 설정을 확인해 주세요.")
    st.stop()

school_title = escape(current_school.get("SCHUL_NM", "우리 학교"))

st.caption(f"🏫 {school_title} · {selected_year}년 {selected_month}월")

# --------------------------------------------------
# 날짜별 데이터 정리
# --------------------------------------------------
meal_by_date = {}
for row in meals:
    raw_date = row.get("MLSV_YMD", "")
    if not raw_date:
        continue

    try:
        meal_date = datetime.strptime(raw_date, "%Y%m%d").date()
    except ValueError:
        continue

    meal_by_date.setdefault(meal_date, []).append(row)

schedule_by_date = {}
for row in schedules:
    raw_date = row.get("AA_YMD", "")
    if not raw_date:
        continue

    try:
        schedule_date = datetime.strptime(raw_date, "%Y%m%d").date()
    except ValueError:
        continue

    schedule_by_date.setdefault(schedule_date, []).append(row)


def clean_menu(text):
    """나이스 메뉴의 HTML 줄바꿈과 알레르기 번호를 정리."""
    if not text:
        return "등록된 메뉴가 없어요."

    import re
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("&amp;", "&").replace("&nbsp;", " ")
    return text.strip() or "등록된 메뉴가 없어요."


def meals_for_day(day):
    rows = meal_by_date.get(day, [])
    lunch, dinner = [], []

    for row in rows:
        kind = row.get("MMEAL_SC_NM", "")
        item = {
            "menu": clean_menu(row.get("DDISH_NM", "")),
            "calories": row.get("CAL_INFO", ""),
        }

        if "중식" in kind:
            lunch.append(item)
        elif "석식" in kind:
            dinner.append(item)

    return lunch, dinner


def schedule_names(day):
    return [
        row.get("EVENT_NM", "").strip()
        for row in schedule_by_date.get(day, [])
        if row.get("EVENT_NM", "").strip()
    ]


# --------------------------------------------------
# 오늘의 요약
# --------------------------------------------------
today_lunch, today_dinner = meals_for_day(today)
today_events = schedule_names(today)

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(
        "🍚 오늘 중식",
        "있음" if today_lunch else "정보 없음",
    )

with metric2:
    st.metric(
        "🌙 오늘 석식",
        "있음" if today_dinner else "정보 없음",
    )

with metric3:
    st.metric(
        "🗓️ 오늘 일정",
        f"{len(today_events)}건",
    )

# 오늘 메뉴 카드
left, right = st.columns(2)

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("### 🍚 오늘의 중식")

    if today_lunch:
        for item in today_lunch:
            st.markdown(
                f'<div class="menu-text">{escape(item["menu"])}</div>',
                unsafe_allow_html=True,
            )
            if item["calories"]:
                st.caption(f'열량: {item["calories"]} kcal')
    else:
        st.info("중식 정보가 없어요. 실제 미제공일인지 확인해 주세요.")

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("### 🌙 오늘의 석식")

    if today_dinner:
        for item in today_dinner:
            st.markdown(
                f'<div class="menu-text">{escape(item["menu"])}</div>',
                unsafe_allow_html=True,
            )
            if item["calories"]:
                st.caption(f'열량: {item["calories"]} kcal')
    else:
        st.info("석식 정보가 없어요. 실제 미제공일인지 확인해 주세요.")

    st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# 학사일정
# --------------------------------------------------
st.markdown("### 🎒 이번 달 학사일정")

events_this_month = []
for event_day, rows in sorted(schedule_by_date.items()):
    for row in rows:
        event_name = row.get("EVENT_NM", "").strip()
        if event_name:
            events_this_month.append(
                (event_day, event_name, row.get("EVENT_CNTNT", "").strip())
            )

if events_this_month:
    for event_day, event_name, detail in events_this_month:
        with st.container(border=True):
            st.markdown(
                f"**{event_day.strftime('%m월 %d일')} · {escape(event_name)}**"
            )
            if detail:
                st.caption(escape(detail))
else:
    st.info("이번 달에 표시할 학사일정 데이터가 없어요.")

# --------------------------------------------------
# 월별 급식표
# --------------------------------------------------
st.markdown(f"### 🥗 {selected_month}월 급식표")
st.caption("날짜를 선택하면 해당 날짜의 중식·석식과 일정을 확인할 수 있어요.")

date_options = [
    date(selected_year, selected_month, d)
    for d in range(1, last_day + 1)
]

selected_day = st.selectbox(
    "상세 확인 날짜",
    date_options,
    index=min(today.day - 1, last_day - 1)
    if (today.year, today.month) == (selected_year, selected_month)
    else 0,
    format_func=lambda d: (
        f"{d.strftime('%m월 %d일')} "
        f"({['월', '화', '수', '목', '금', '토', '일'][d.weekday()]})"
    ),
)

detail_lunch, detail_dinner = meals_for_day(selected_day)
detail_events = schedule_names(selected_day)

d1, d2 = st.columns(2)

with d1:
    st.markdown("#### 🍚 중식")
    if detail_lunch:
        for item in detail_lunch:
            st.markdown(item["menu"])
            if item["calories"]:
                st.caption(f'열량: {item["calories"]} kcal')
    else:
        st.warning("중식 데이터 없음 · 미제공 여부 확인 필요")

with d2:
    st.markdown("#### 🌙 석식")
    if detail_dinner:
        for item in detail_dinner:
            st.markdown(item["menu"])
            if item["calories"]:
                st.caption(f'열량: {item["calories"]} kcal')
    else:
        st.warning("석식 데이터 없음 · 미제공 여부 확인 필요")

st.markdown("#### 📌 선택한 날짜의 학사일정")
if detail_events:
    for event in detail_events:
        st.write(f"• {event}")
else:
    st.caption("등록된 일정이 없어요.")

# --------------------------------------------------
# 급식 미제공 가능일 안내
# --------------------------------------------------
st.markdown("### 🔔 미리 확인할 날짜")

weekdays_without_meal = []
for day in date_options:
    if day.weekday() >= 5:
        continue

    lunch, dinner = meals_for_day(day)
    if not lunch and not dinner:
        weekdays_without_meal.append(day)

if weekdays_without_meal:
    st.warning(
        "평일 중 급식 데이터가 확인되지 않는 날짜가 있어요. "
        "아래 날짜는 미제공 확정이 아니라 확인이 필요한 날짜예요."
    )

    st.write(
        " · ".join(
            day.strftime("%m/%d")
            for day in weekdays_without_meal
        )
    )
else:
    st.success(
        "급식 데이터가 없는 평일이 발견되지 않았어요. "
        "실제 제공 여부는 학교 공지도 함께 확인해 주세요."
    )

st.caption(
    "※ 이 앱은 자동 푸시 알림을 보내지 않아요. "
    "급식 데이터 누락은 실제 미제공과 다를 수 있으며, "
    "급식 운영 여부는 학교의 공식 공지를 최종 확인해 주세요."
)

st.divider()
st.caption("급식식 알뜰알림 · 학교생활을 더 간편하게 🍀")
