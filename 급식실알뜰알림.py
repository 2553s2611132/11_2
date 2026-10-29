
import calendar
import os
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import streamlit as st

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="급식실 알뜰알림",
    page_icon="🍚",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_URL = "https://open.neis.go.kr/hub"
SEOUL_TZ = ZoneInfo("Asia/Seoul")
SCHOOL_NAME = "천안오성고등학교"
SCHOOL_REGION = "충청남도"
TIMEOUT = 12

# NEIS_API_KEY는 Streamlit Secrets에서 읽습니다.
# 키가 없더라도 앱 화면은 열리지만 조회 건수가 제한될 수 있습니다.
try:
    API_KEY = st.secrets.get("NEIS_API_KEY", "")
except Exception:
    API_KEY = os.getenv("NEIS_API_KEY", "")

# --------------------------------------------------
# 디자인
# --------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F7F9FC;
    }
    .main-title {
        font-size: 2.35rem;
        font-weight: 850;
        color: #173B65;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #64748B;
        font-size: 1rem;
        margin-bottom: 1.4rem;
    }
    .info-card {
        background: white;
        padding: 18px;
        border-radius: 15px;
        border: 1px solid #E2E8F0;
        margin-bottom: 10px;
    }
    .small-label {
        color: #64748B;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# 공통 API 함수
# --------------------------------------------------
def neis_request(endpoint, params):
    """NEIS API 요청 및 응답 검증."""
    request_params = {
        "Type": "json",
        **params,
    }

    if API_KEY:
        request_params["KEY"] = API_KEY

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=request_params,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.Timeout as exc:
        raise RuntimeError(
            "나이스 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(
            "나이스 서버에 연결하지 못했습니다. 인터넷 연결을 확인해 주세요."
        ) from exc
    except ValueError as exc:
        raise RuntimeError(
            "나이스에서 올바른 JSON 데이터를 받지 못했습니다."
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError("나이스 응답 형식이 올바르지 않습니다.")

    result = data.get("RESULT")
    if result and result.get("CODE") not in (None, "INFO-000"):
        code = result.get("CODE", "")
        message = result.get("MESSAGE", "알 수 없는 오류")

        if code == "INFO-200":
            return []

        raise RuntimeError(f"나이스 API 오류 ({code}): {message}")

    return data


def extract_rows(data, endpoint):
    """NEIS 응답에서 row 목록을 안전하게 추출."""
    section = data.get(endpoint)

    if not section:
        return []

    if not isinstance(section, list):
        return []

    for item in section:
        if isinstance(item, dict) and isinstance(item.get("row"), list):
            return item["row"]

    return []


def get_total_count(data, endpoint):
    """응답의 전체 데이터 건수 추출."""
    section = data.get(endpoint, [])

    if not isinstance(section, list):
        return 0

    for item in section:
        if not isinstance(item, dict):
            continue

        for head in item.get("head", []):
            if not isinstance(head, dict):
                continue

            if "list_total_count" in head:
                try:
                    return int(head["list_total_count"])
                except (ValueError, TypeError):
                    return 0

    return 0


def fetch_all_rows(endpoint, params, page_size=1000):
    """페이지를 나누어 데이터를 가져옵니다."""
    all_rows = []
    page = 1

    while page <= 20:
        page_params = {
            **params,
            "pIndex": page,
            "pSize": page_size,
        }

        data = neis_request(endpoint, page_params)
        rows = extract_rows(data, endpoint)

        if not rows:
            break

        all_rows.extend(rows)
        total = get_total_count(data, endpoint)

        if total == 0 or len(all_rows) >= total:
            break

        if len(rows) < page_size:
            break

        page += 1

    return all_rows


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def find_school():
    """충청남도 천안오성고등학교의 NEIS 학교 코드를 찾습니다."""
    data = neis_request(
        "schoolInfo",
        {
            "SCHUL_NM": SCHOOL_NAME,
            "LCTN_SC_NM": SCHOOL_REGION,
            "pIndex": 1,
            "pSize": 100,
        },
    )

    rows = extract_rows(data, "schoolInfo")

    # 정확한 학교명을 우선 선택합니다.
    matches = [
        row for row in rows
        if row.get("SCHUL_NM", "").strip() == SCHOOL_NAME
    ]

    # 지역명 표기가 다른 경우에도 정확한 학교명을 검색합니다.
    if not matches:
        matches = [
            row for row in rows
            if SCHOOL_NAME in row.get("SCHUL_NM", "")
        ]

    if not matches:
        raise RuntimeError(
            "천안오성고등학교를 찾지 못했습니다. "
            "학교명 또는 나이스 API 응답을 확인해 주세요."
        )

    return matches[0]


# --------------------------------------------------
# 급식 조회
# --------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_meals(office_code, school_code, start_date, end_date):
    """선택한 기간의 급식 데이터를 조회합니다."""
    return fetch_all_rows(
        "mealServiceDietInfo",
        {
            "ATPT_OFCDC_SC_CODE": office_code,
            "SD_SCHUL_CODE": school_code,
            "MLSV_FROM_YMD": start_date.strftime("%Y%m%d"),
            "MLSV_TO_YMD": end_date.strftime("%Y%m%d"),
        },
    )


# --------------------------------------------------
# 학사일정 조회
# --------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_schedules(office_code, school_code, year, start_date, end_date):
    """선택한 기간의 학교 학사일정을 조회합니다."""
    return fetch_all_rows(
        "SchoolSchedule",
        {
            "ATPT_OFCDC_SC_CODE": office_code,
            "SD_SCHUL_CODE": school_code,
            "AY": str(year),
            "AA_FROM_YMD": start_date.strftime("%Y%m%d"),
            "AA_TO_YMD": end_date.strftime("%Y%m%d"),
        },
    )


# --------------------------------------------------
# 데이터 정리
# --------------------------------------------------
def clean_menu(value):
    """메뉴의 HTML 줄바꿈과 불필요한 공백을 정리합니다."""
    text = str(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    return text.strip()


def parse_ymd(value):
    """YYYYMMDD 형식의 날짜를 date로 변환합니다."""
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def get_meal_type(row):
    """급식 종류를 이름과 코드로 판별합니다."""
    name = str(row.get("MMEAL_SC_NM", "")).strip()
    code = str(row.get("MMEAL_SC_CODE", "")).strip()

    if "조식" in name or code == "1":
        return "조식"
    if "중식" in name or code == "2":
        return "중식"
    if "석식" in name or code == "3":
        return "석식"

    return name or "기타"


def get_calendar_event(row):
    """학사일정의 표시용 날짜와 행사명을 정리합니다."""
    event_date = parse_ymd(row.get("AA_YMD"))

    return {
        "date": event_date,
        "name": str(row.get("EVENT_NM", "")).strip(),
        "content": str(row.get("EVENT_CNTNT", "")).strip(),
    }


def is_likely_no_school(event_name, content=""):
    """학교 휴업 가능성이 있는 일정인지 확인합니다."""
    text = f"{event_name} {content}"

    keywords = (
        "방학", "휴업", "재량휴업", "공휴일",
        "개교기념일", "대체공휴일",
    )

    return any(keyword in text for keyword in keywords)


def format_date(day):
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return f"{day.month}월 {day.day}일 ({weekdays[day.weekday()]})"


# --------------------------------------------------
# 앱 화면
# --------------------------------------------------
st.markdown(
    '<div class="main-title">🍚 급식실 알뜰알림</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-title">'
    '오늘의 식단부터 학교 일정까지, 한눈에 확인하세요.'
    '</div>',
    unsafe_allow_html=True,
)

today = datetime.now(SEOUL_TZ).date()

with st.sidebar:
    st.title("📅 조회 설정")
    st.caption(SCHOOL_NAME)
    st.divider()

    year = st.selectbox(
        "연도",
        options=list(range(today.year - 1, today.year + 3)),
        index=1,
    )

    month = st.selectbox(
        "월",
        options=list(range(1, 13)),
        index=today.month - 1,
        format_func=lambda m: f"{m}월",
    )

    st.divider()
    st.caption("데이터 출처: 교육부 NEIS 공개 API")
    st.caption("식단 및 일정은 학교의 최신 등록 내용에 따라 달라질 수 있습니다.")

start_date = date(year, month, 1)
end_date = date(year, month, calendar.monthrange(year, month)[1])

# --------------------------------------------------
# 학교 정보 및 월별 데이터 불러오기
# --------------------------------------------------
try:
    with st.spinner("학교 정보와 데이터를 불러오는 중입니다..."):
        school = find_school()

        office_code = school["ATPT_OFCDC_SC_CODE"]
        school_code = school["SD_SCHUL_CODE"]

        meals = get_meals(
            office_code, school_code, start_date, end_date
        )

        schedules = get_schedules(
            office_code, school_code, year, start_date, end_date
        )

except RuntimeError as exc:
    st.error(str(exc))
    st.info(
        "NEIS_API_KEY를 설정했는지 확인하고, "
        "나이스 API 서비스 상태를 확인한 뒤 다시 시도해 주세요."
    )
    st.stop()

except Exception:
    st.error(
        "데이터를 처리하는 중 예상하지 못한 오류가 발생했습니다. "
        "잠시 후 다시 시도해 주세요."
    )
    st.stop()

st.success(f"🏫 {school.get('SCHUL_NM', SCHOOL_NAME)}")

# 날짜별 데이터 묶기
meals_by_date = {}
for row in meals:
    meal_date = parse_ymd(row.get("MLSV_YMD"))
    if meal_date:
        meals_by_date.setdefault(meal_date, []).append(row)

events_by_date = {}
for row in schedules:
    event = get_calendar_event(row)
    if event["date"]:
        events_by_date.setdefault(event["date"], []).append(event)

# --------------------------------------------------
# 상단 요약 카드
# --------------------------------------------------
today_meals = meals_by_date.get(today, [])
today_events = events_by_date.get(today, [])

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("선택한 달", f"{year}년 {month}월")

with col2:
    st.metric("급식 데이터가 있는 날", len(meals_by_date))

with col3:
    st.metric("등록된 학사일정", sum(map(len, events_by_date.values())))

# --------------------------------------------------
# 탭
# --------------------------------------------------
tab_today, tab_month, tab_schedule, tab_alert = st.tabs(
    ["🏠 오늘의 정보", "🍱 월별 급식표", "🗓️ 학사일정", "🔔 미급식 확인"]
)

with tab_today:
    st.subheader(f"오늘의 정보 · {format_date(today)}")

    if today_meals:
        for row in sorted(today_meals, key=get_meal_type):
            with st.container(border=True):
                st.markdown(f"### 🍽️ {get_meal_type(row)}")

                menu = clean_menu(row.get("DDISH_NM", ""))
                if menu:
                    for dish in menu.splitlines():
                        if dish.strip():
                            st.write(f"• {dish.strip()}")
                else:
                    st.info("메뉴가 등록되지 않았습니다.")

                calories = str(row.get("CAL_INFO", "")).strip()
                if calories:
                    st.caption(f"열량: {calories}")
    else:
        st.info(
            "오늘의 급식 데이터가 없습니다. "
            "급식이 없는 날인지, 아직 데이터가 등록되지 않은 것인지 "
            "학교 공지를 확인해 주세요."
        )

    st.markdown("### 📌 오늘의 학사일정")

    if today_events:
        for event in today_events:
            st.write(f"• **{event['name'] or '학교 일정'}**")
            if event["content"]:
                st.caption(event["content"])
    else:
        st.write("등록된 오늘의 학사일정이 없습니다.")

with tab_month:
    st.subheader(f"🍱 {year}년 {month}월 급식표")

    if not meals:
        st.info(
            "선택한 달의 급식 데이터가 없습니다. "
            "인증키 설정과 나이스 등록 여부를 확인해 주세요."
        )
    else:
        for week_start in range(1, end_date.day + 1, 7):
            week_end = min(week_start + 6, end_date.day)

            st.markdown(f"#### {month}월 {week_start}일 ~ {week_end}일")
            cols = st.columns(2)

            for day_num in range(week_start, week_end + 1):
                current_date = date(year, month, day_num)
                day_meals = meals_by_date.get(current_date, [])
                day_events = events_by_date.get(current_date, [])

                with cols[(day_num - week_start) % 2]:
                    with st.container(border=True):
                        st.markdown(f"**{format_date(current_date)}**")

                        if day_events:
                            for event in day_events:
                                st.caption(f"📌 {event['name']}")

                        if day_meals:
                            for row in sorted(day_meals, key=get_meal_type):
                                st.markdown(f"**{get_meal_type(row)}**")
                                menu = clean_menu(row.get("DDISH_NM", ""))
                                st.write(menu or "메뉴 정보 없음")

                                calories = str(row.get("CAL_INFO", "")).strip()
                                if calories:
                                    st.caption(f"열량: {calories}")
                        elif current_date.weekday() >= 5:
                            st.caption("주말 · 급식 데이터 없음")
                        else:
                            st.warning("급식 데이터 없음 · 미급식 여부 확인 필요")

with tab_schedule:
    st.subheader(f"🗓️ {year}년 {month}월 학사일정")

    event_list = []
    for day, day_events in sorted(events_by_date.items()):
        for event in day_events:
            event_list.append((day, event))

    if event_list:
        for day, event in event_list:
            with st.container(border=True):
                st.markdown(f"**{format_date(day)}**")
                st.write(event["name"] or "학교 일정")
                if event["content"]:
                    st.caption(event["content"])

                if is_likely_no_school(
                    event["name"], event["content"]
                ):
                    st.info(
                        "휴업 또는 방학 관련 일정일 수 있습니다. "
                        "실제 급식 제공 여부는 학교 공지로 확인하세요."
                    )
    else:
        st.info("선택한 달에 등록된 학사일정이 없습니다.")

with tab_alert:
    st.subheader("🔔 급식·석식 미제공 여부 확인")
    st.write(
        "급식 데이터가 없는 날짜와 휴업 관련 일정을 모아 보여 줍니다. "
        "데이터 누락과 실제 미급식일은 다를 수 있습니다."
    )

    missing_dates = []

    for day_num in range(1, end_date.day + 1):
        current_date = date(year, month, day_num)

        # 주말은 일반적인 평일 급식 누락 알림에서 제외
        if current_date.weekday() >= 5:
            continue

        day_meals = meals_by_date.get(current_date, [])
        day_events = events_by_date.get(current_date, [])

        event_names = [
            event["name"] for event in day_events if event["name"]
        ]

        meal_types = {get_meal_type(row) for row in day_meals}
        no_school_event = any(
            is_likely_no_school(event["name"], event["content"])
            for event in day_events
        )

        missing_lunch = "중식" not in meal_types
        missing_dinner = "석식" not in meal_types

        if missing_lunch or missing_dinner or no_school_event:
            missing_dates.append(
                (
                    current_date,
                    missing_lunch,
                    missing_dinner,
                    no_school_event,
                    event_names,
                )
            )

    if not missing_dates:
        st.success(
            "선택한 달에 확인이 필요한 평일이 없습니다. "
            "다만 급식 운영 여부는 학교 공지와 대조해 주세요."
        )
    else:
        for day, missing_lunch, missing_dinner, no_school_event, names in missing_dates:
            with st.container(border=True):
                st.markdown(f"### 📅 {format_date(day)}")

                if no_school_event:
                    st.warning(
                        "휴업·방학 관련 일정이 있습니다. "
                        "급식 운영 여부를 확인해 주세요."
                    )

                if missing_lunch:
                    st.write("⚠️ 중식 데이터 없음 — 실제 미급식 여부 확인 필요")

                if missing_dinner:
                    st.write("⚠️ 석식 데이터 없음 — 실제 미급식 여부 확인 필요")

                if names:
                    st.caption("학사일정: " + ", ".join(names))

    st.divider()
    st.caption(
        "이 앱은 별도 푸시 알림을 전송하지 않습니다. "
        "화면에서 확인할 수 있는 사전 점검 기능입니다."
    )

# --------------------------------------------------
# 하단 안내
# --------------------------------------------------
st.divider()
st.caption(
    "급식실 알뜰알림 · 교육부 NEIS 공개 데이터 기반 · "
    "데이터 갱신 및 급식 변경 사항은 학교 공식 안내를 우선합니다."
)
