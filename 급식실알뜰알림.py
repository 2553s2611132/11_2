
def clean_menu(value):
    """NEIS 메뉴의 HTML 줄바꿈 및 알레르기 번호 표기를 정리합니다."""
    return str(value or "").replace("<br/>", "\n").replace("<br />", "\n").replace("<br>", "\n").strip()


def parse_ymd(value):
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def main():
    st.markdown(
        """
        <style>
        .main .block-container {max-width: 1100px; padding-top: 1.8rem;}
        .hero {
            padding: 1.4rem 1.5rem; border-radius: 18px;
            background: linear-gradient(120deg, #e8f5e9, #fff8e1);
            border: 1px solid #dcebdc; margin-bottom: 1rem;
        }
        .hero h1 {margin: 0; color: #1b4332; font-size: 2rem;}
        .hero p {margin: .45rem 0 0; color: #355e4a;}
        </style>
        <div class="hero">
          <h1>🍱 급식실 알뜰 알림</h1>
          <p>천안오성고등학교의 월간 급식표와 학사일정을 한눈에 확인해요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    api_key = get_api_key()
    if not api_key:
        st.error("NEIS API 키가 설정되지 않았어요.")
        st.markdown(
            """
            1. [나이스 교육정보 개방 포털](https://open.neis.go.kr/)에 접속해 로그인하세요.
            2. 인증키 신청 메뉴에서 Open API 인증키를 발급받으세요.
            3. Streamlit Community Cloud의 **App → Settings → Secrets**에 아래 내용을 입력하세요.

            ```toml
            NEIS_API_KEY = "발급받은_인증키"
            ```

            로컬 실행 시에는 프로젝트 폴더에 `.streamlit/secrets.toml` 파일을 만들고 같은 내용을 넣으면 됩니다.
            """
        )
        st.stop()

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    years = list(range(today.year - 1, today.year + 3))
    c1, c2 = st.columns([1, 1])
    with c1:
        year = st.selectbox("연도", years, index=years.index(today.year))
    with c2:
        month = st.selectbox("월", list(range(1, 13)), index=today.month - 1, format_func=lambda m: f"{m}월")

    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])
    start_ymd = start_date.strftime("%Y%m%d")
    end_ymd = end_date.strftime("%Y%m%d")

    try:
        with st.spinner("천안오성고등학교 정보를 불러오는 중..."):
            office_code, school_code, school_name = find_school(api_key)
            meals = get_meals(api_key, office_code, school_code, start_ymd, end_ymd)
            schedules = get_schedule(api_key, office_code, school_code, start_ymd, end_ymd)
    except RuntimeError as exc:
        st.error(str(exc))
        st.info("잠시 후 다시 시도하거나, 나이스 API 키와 학교 정보가 올바른지 확인해 주세요.")
        if st.button("다시 불러오기"):
            st.cache_data.clear()
            st.rerun()
        st.stop()
    except Exception as exc:
        st.error("예상하지 못한 오류가 발생했어요.")
        st.caption(f"오류 유형: {type(exc).__name__}")
        st.info("페이지를 새로고침해 주세요. 문제가 계속되면 API 설정을 확인해 주세요.")
        st.stop()

    st.caption(f"📍 {school_name} · 데이터 출처: 교육부 나이스(NEIS) · 조회 기간: {year}년 {month}월")

    meal_by_date = {}
    for row in meals:
        day = parse_ymd(row.get("MLSV_YMD"))
        if not day:
            continue
        meal_by_date.setdefault(day, {})[str(row.get("MMEAL_SC_CODE", ""))] = row

    schedule_by_date = {}
    for row in schedules:
        day = parse_ymd(row.get("AA_YMD"))
        if not day:
            continue
        event = str(row.get("EVENT_NM", "")).strip()
        detail = str(row.get("EVENT_CNTNT", "")).strip()
        if event or detail:
            text = event
            if detail and detail != event:
                text = f"{event} — {detail}" if event else detail
            schedule_by_date.setdefault(day, []).append(text)

    lunch_count = sum(1 for items in meal_by_date.values() if items.get("2", {}).get("DDISH_NM"))
    dinner_count = sum(1 for items in meal_by_date.values() if items.get("3", {}).get("DDISH_NM"))
    event_count = sum(len(v) for v in schedule_by_date.values())

    m1, m2, m3 = st.columns(3)
    m1.metric("점심 메뉴 등록", f"{lunch_count}일")
    m2.metric("석식 메뉴 등록", f"{dinner_count}일")
    m3.metric("학사일정", f"{event_count}건")

    tab_meals, tab_alerts, tab_calendar = st.tabs(["🥗 월간 급식표", "🔔 급식 확인 알림", "🗓️ 학사일정"])

    with tab_meals:
        st.subheader(f"{month}월 급식표")
        if not meal_by_date:
            st.warning("선택한 달의 급식 데이터가 없어요. 방학 기간이거나 나이스에 아직 등록되지 않았을 수 있어요.")
        else:
            rows = []
            for day in sorted(meal_by_date):
                items = meal_by_date[day]
                lunch = clean_menu(items.get("2", {}).get("DDISH_NM", ""))
                dinner = clean_menu(items.get("3", {}).get("DDISH_NM", ""))
                rows.append(
                    {
                        "날짜": day.strftime("%m월 %d일 (%a)"),
                        "중식": lunch.replace("\n", " · ") if lunch else "등록된 메뉴 없음",
                        "석식": dinner.replace("\n", " · ") if dinner else "등록된 메뉴 없음",
                        "알림": "석식 미등록" if lunch and not dinner else ("급식 데이터 확인 필요" if not lunch and not dinner else ""),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.caption("※ ‘등록된 메뉴 없음’은 나이스에 메뉴가 없다는 뜻이며, 실제 급식 운영 여부를 확정하는 표시는 아닙니다.")

        with st.expander("알레르기 번호 안내"):
            st.write(
                "1 난류 · 2 우유 · 3 메밀 · 4 땅콩 · 5 대두 · 6 밀 · 7 고등어 · "
                "8 게 · 9 새우 · 10 돼지고기 · 11 복숭아 · 12 토마토 · 13 아황산류 · "
                "14 호두 · 15 닭고기 · 16 쇠고기 · 17 오징어 · 18 조개류 · 19 잣"
            )
            st.caption("메뉴에 표시되는 숫자는 알레르기 유발 식재료 번호입니다.")

    with tab_alerts:
        st.subheader("급식 확인이 필요한 날")
        alert_items = []
        for day in sorted(set(meal_by_date) | set(schedule_by_date)):
            items = meal_by_date.get(day, {})
            lunch = clean_menu(items.get("2", {}).get("DDISH_NM", ""))
            dinner = clean_menu(items.get("3", {}).get("DDISH_NM", ""))
            events = schedule_by_date.get(day, [])
            notes = []
            if lunch and not dinner:
                notes.append("석식 메뉴 미등록")
            if not lunch and not dinner and events:
                notes.append("급식 메뉴 미등록")
            if any(keyword in " ".join(events) for keyword in ("방학", "공휴일", "재량휴업", "개교기념")):
                notes.append("휴업 관련 일정 확인")
