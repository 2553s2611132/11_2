# -*- coding: utf-8 -*-
"""급식실 도우미 - 급식 정보 / 학년 순서 / 자리 현황 / 급식 운세 / 조리 도우미
AI 없이 동작하므로 API 키(Secrets)가 필요 없습니다."""

import hashlib
import html
import math
import random
from datetime import datetime, timedelta, timezone

import streamlit as st

# ------------------------------------------------------------------
# 0. 기본 설정 (여기만 바꾸면 우리 학교용으로 사용할 수 있어요)
# ------------------------------------------------------------------
SCHOOL_NAME = "서울중앙중학교"      # 학교 이름
START_MIN = 12 * 60 + 10            # 배식 시작 시각 (12:10)
GAP_MIN = 3                         # 학년 사이 이동·정리 시간(분)
TABLE_CAP = 12                      # 테이블 1개당 좌석 수
TABLE_NAMES = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"]
INITIAL_SEATS = {"A1": 4, "A2": 8, "A3": 12, "B1": 2, "B2": 12,
                 "B3": 10, "C1": 12, "C2": 0, "C3": 6}
DAYS = ["월", "화", "수", "목", "금"]
KST = timezone(timedelta(hours=9))

# 요일별 급식 (예시 데이터 - 학교 급식표에 맞게 고치세요)
MENU = {
    0: {"kcal": 702, "items": ["잡곡밥", "미역국", "제육볶음", "감자채볶음", "배추김치"],
        "allergy": "대두, 밀, 돼지고기, 쇠고기"},
    1: {"kcal": 668, "items": ["흑미밥", "된장찌개", "닭갈비", "청포묵무침", "깍두기"],
        "allergy": "대두, 밀, 닭고기"},
    2: {"kcal": 685, "items": ["잡곡밥", "순두부찌개", "닭강정", "배추김치", "우유"],
        "allergy": "난류, 우유, 대두, 밀, 닭고기"},
    3: {"kcal": 720, "items": ["카레라이스", "콩나물국", "군만두", "단무지", "사과"],
        "allergy": "난류, 대두, 밀, 돼지고기"},
    4: {"kcal": 690, "items": ["비빔밥", "어묵국", "계란말이", "깍두기", "요구르트"],
        "allergy": "난류, 우유, 대두, 밀"},
}

# 1인분 기준량 (조리 도우미용)
STANDARD = [("쌀 (밥)", 90, "g"), ("국·찌개", 250, "ml"), ("주 반찬", 90, "g"),
            ("부 반찬", 50, "g"), ("김치", 40, "g")]

LEVELS = [("대길", 5), ("길", 4), ("중길", 3), ("소길", 2)]
MESSAGES = [
    "{menu} 한 입이면 오후 수업도 거뜬해요.",
    "친구와 함께 먹으면 {menu} 맛이 두 배!",
    "{menu} 앞에서 차례를 지키면 복이 따라와요.",
    "오늘은 {menu} 덕분에 기분 좋은 일이 생길 거예요.",
    "{menu}, 남기지 않고 먹으면 키가 쑥쑥 커요.",
]
TIPS = [
    "급식 아주머니께 '잘 먹겠습니다' 한마디 하면 행운이 두 배예요.",
    "줄을 설 때 한 걸음씩 천천히, 서두르지 않는 게 오늘의 행운 열쇠!",
    "식판은 깔끔하게 비우고 자리는 깨끗하게 정리해요.",
]

CSS = """
<style>
.block-container{padding-top:2rem;max-width:720px}
.lz-hd .lz-sub{color:#4A5F57;font-size:14px}
.lz-hd h1{margin:0;padding:0;font-size:30px;font-weight:900;color:#13302A}
.lz-card{background:#fff;border-radius:24px;padding:20px;margin:6px 0 14px;color:#13302A}
.lz-tag{color:#1F6B4F;font-weight:700;font-size:13px}
.lz-menu{font-size:18px;line-height:1.8;margin-top:8px}
.lz-sub{color:#4A5F57;font-size:13px}
.lz-row{display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:18px;background:#fff;color:#13302A;margin-bottom:8px}
.lz-row.lz-now{background:#FFB84D}
.lz-no{width:36px;height:36px;border-radius:50%;background:#E4ECE2;display:flex;align-items:center;justify-content:center;font-weight:900;flex:none}
.lz-now .lz-no{background:#13302A;color:#fff}
.lz-g{font-size:17px;font-weight:700;flex:1}
.lz-tm{font-size:13px;text-align:right}
.lz-pill{font-size:12px;font-weight:700;padding:5px 10px;border-radius:99px;background:#E4ECE2;flex:none}
.lz-now .lz-pill{background:#13302A;color:#fff}
.lz-strip{background:#DCE5DA;border-radius:12px;padding:8px;text-align:center;font-size:13px;font-weight:700;color:#13302A;margin:8px 0}
.lz-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}
.lz-tb{border-radius:16px;height:80px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:12px;font-weight:700}
.lz-tb b{font-size:18px}
.lz-a{background:#D3EEDD;color:#13302A}
.lz-b{background:#FFD98A;color:#13302A}
.lz-f{background:#13302A;color:#fff}
.lz-big{background:#13302A;color:#fff;border-radius:24px;padding:20px;margin:6px 0 12px}
.lz-big .n{font-size:48px;font-weight:900;line-height:1.1}
.lz-fort{background:#FFB84D;border-radius:24px;padding:28px 24px;text-align:center;color:#13302A;margin:10px 0 14px}
.lz-fort .big{font-size:64px;font-weight:900;line-height:1.1}
.lz-fort .st{font-size:24px;letter-spacing:4px}
.lz-fort p{margin:12px 0 0;font-size:17px;font-weight:500;line-height:1.6}
.lz-lk{display:flex;gap:10px;margin-bottom:12px}
.lz-lk div{flex:1;background:#fff;border-radius:20px;padding:14px 8px;text-align:center;font-size:16px;font-weight:700;color:#13302A}
.lz-lk span{display:block;font-size:13px;font-weight:400;color:#4A5F57}
</style>
"""


# ------------------------------------------------------------------
# 1. 도우미 함수
# ------------------------------------------------------------------
def get_int(key, default):
    """session_state에서 정수 값을 안전하게 읽기"""
    try:
        return int(st.session_state.get(key, default))
    except (TypeError, ValueError):
        return default


def fmt_time(minutes):
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def grade_order(day_idx):
    """요일마다 먼저 먹는 학년이 돌아가도록 순서 만들기"""
    cyc = [1, 2, 3]
    start = day_idx % 3
    return cyc[start:] + cyc[:start]


def make_plan(order, counts, lines, rate):
    """학년별 배식 시작/종료 시각 계산"""
    plan = []
    t = START_MIN
    per_min = max(1, lines * rate)
    for g in order:
        n = max(0, counts.get(g, 0))
        dur = math.ceil(n / per_min) if n > 0 else 0
        plan.append({"grade": g, "n": n, "start": t, "end": t + dur})
        t += dur + GAP_MIN
    return plan


def seat_status(n):
    if n >= TABLE_CAP:
        return "만석", "lz-f"
    if n * 2 >= TABLE_CAP:
        return "보통", "lz-b"
    return "여유", "lz-a"


def change_seat(delta):
    t = st.session_state.get("sel_table", TABLE_NAMES[0])
    seats = st.session_state["seats"]
    seats[t] = max(0, min(TABLE_CAP, seats.get(t, 0) + delta))


def clear_table():
    t = st.session_state.get("sel_table", TABLE_NAMES[0])
    st.session_state["seats"][t] = 0


def reset_all():
    st.session_state["seats"] = {t: 0 for t in TABLE_NAMES}


def show_fortune():
    st.session_state["f_on"] = True


def make_fortune(day_key, name, grade, items):
    seed_text = "%s|%s|%s" % (day_key, grade, name.strip())
    seed = int(hashlib.md5(seed_text.encode("utf-8")).hexdigest(), 16) % (10 ** 8)
    rng = random.Random(seed)
    level, stars = rng.choices(LEVELS, weights=[2, 4, 3, 1])[0]
    lucky_menu = rng.choice(items)
    return {
        "level": level,
        "stars": stars,
        "msg": rng.choice(MESSAGES).format(menu=lucky_menu),
        "menu": lucky_menu,
        "seat": rng.choice(TABLE_NAMES),
        "time": fmt_time(rng.choice(range(START_MIN, 13 * 60, 5))),
        "tip": rng.choice(TIPS),
    }


# ------------------------------------------------------------------
# 2. 화면
# ------------------------------------------------------------------
def tab_menu(now, weekday, is_weekend, today_idx):
    day = st.selectbox("요일 선택", DAYS, index=today_idx, key="day_sel")
    day_idx = DAYS.index(day)
    is_today = (not is_weekend) and day_idx == weekday
    if is_weekend:
        st.caption("오늘은 주말이에요. 월요일부터 확인해 보세요.")

    m = MENU[day_idx]
    st.markdown(
        '<div class="lz-card"><div class="lz-tag">중식 · %d kcal</div>'
        '<div class="lz-menu">%s</div>'
        '<div class="lz-sub" style="margin-top:10px">알레르기: %s</div></div>'
        % (m["kcal"], "<br>".join(m["items"]), m["allergy"]),
        unsafe_allow_html=True,
    )

    st.markdown("#### 배식 순서")
    counts = {1: get_int("n1", 320), 2: get_int("n2", 310), 3: get_int("n3", 300)}
    plan = make_plan(grade_order(day_idx), counts,
                     get_int("lines", 2), get_int("rate", 8))
    now_min = now.hour * 60 + now.minute
    rows = []
    for i, p in enumerate(plan, start=1):
        if not is_today:
            status, cls = "예정", ""
        elif p["start"] <= now_min < p["end"]:
            status, cls = "배식 중", "lz-now"
        elif now_min >= p["end"]:
            status, cls = "완료", ""
        else:
            status, cls = "대기", ""
        rows.append(
            '<div class="lz-row %s"><span class="lz-no">%d</span>'
            '<span class="lz-g">%d학년</span>'
            '<span class="lz-tm">%s~%s<br>%d명</span>'
            '<span class="lz-pill">%s</span></div>'
            % (cls, i, p["grade"], fmt_time(p["start"]), fmt_time(p["end"]),
               p["n"], status)
        )
    st.markdown("".join(rows), unsafe_allow_html=True)
    st.caption("요일마다 먼저 먹는 학년이 돌아가요. 인원·배식 라인은 '조리 도우미'에서 바꿀 수 있어요.")
    return m


def tab_seats():
    if "seats" not in st.session_state:
        st.session_state["seats"] = dict(INITIAL_SEATS)
    seats = st.session_state["seats"]

    total_cap = TABLE_CAP * len(TABLE_NAMES)
    used = sum(min(TABLE_CAP, max(0, seats.get(t, 0))) for t in TABLE_NAMES)
    left = total_cap - used
    st.markdown(
        '<div class="lz-big"><div class="lz-sub" style="color:#D3EEDD">남은 자리</div>'
        '<div><span class="n">%d</span> / %d석</div></div>' % (left, total_cap),
        unsafe_allow_html=True,
    )
    st.progress(min(1.0, max(0.0, used / total_cap)))

    cells = []
    for t in TABLE_NAMES:
        n = seats.get(t, 0)
        label, cls = seat_status(n)
        cells.append('<div class="lz-tb %s"><b>%s</b><span>%d/%d</span><span>%s</span></div>'
                     % (cls, t, n, TABLE_CAP, label))
    st.markdown('<div class="lz-strip">배식대</div><div class="lz-grid">%s</div>'
                % "".join(cells), unsafe_allow_html=True)

    open_tables = [t for t in TABLE_NAMES if seats.get(t, 0) < TABLE_CAP]
    if open_tables:
        best = min(open_tables, key=lambda t: seats.get(t, 0))
        st.success("학생 안내 추천: %s 테이블이 가장 비어 있어요." % best)
    else:
        st.warning("모든 테이블이 가득 찼어요. 잠시 대기를 안내해 주세요.")

    st.markdown("#### 자리 수정 (직원용)")
    st.selectbox("테이블 선택", TABLE_NAMES, key="sel_table")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.button("−5", on_click=change_seat, args=(-5,), key="m5", use_container_width=True)
    c2.button("−1", on_click=change_seat, args=(-1,), key="m1", use_container_width=True)
    c3.button("+1", on_click=change_seat, args=(1,), key="p1", use_container_width=True)
    c4.button("+5", on_click=change_seat, args=(5,), key="p5", use_container_width=True)
    c5.button("비우기", on_click=clear_table, key="clr", use_container_width=True)
    st.button("전체 테이블 비우기", on_click=reset_all, key="rst")
    st.caption("입력한 값은 이 화면(브라우저 접속)에서만 유지돼요.")


def tab_fortune(now, items):
    st.markdown("#### 오늘의 급식 운세")
    name = st.text_input("이름 또는 별명 (선택)", key="f_name", max_chars=20)
    grade = st.selectbox("누구신가요?", ["1학년", "2학년", "3학년", "선생님", "급식실 가족"],
                         key="f_grade")
    st.button("운세 뽑기", on_click=show_fortune, key="f_btn")

    if st.session_state.get("f_on"):
        f = make_fortune(now.strftime("%Y-%m-%d"), name, grade, items)
        stars = "★" * f["stars"] + "☆" * (5 - f["stars"])
        st.markdown(
            '<div class="lz-fort"><div style="font-size:14px;font-weight:700">'
            '%s님의 오늘 운세</div><div class="big">%s</div>'
            '<div class="st" role="img" aria-label="별 %d개">%s</div><p>%s</p></div>'
            '<div class="lz-lk"><div><span>행운의 메뉴</span>%s</div>'
            '<div><span>행운의 자리</span>%s</div>'
            '<div><span>행운의 시간</span>%s</div></div>'
            % (html.escape(name.strip()) or "오늘의 주인공", f["level"], f["stars"],
               stars, f["msg"], f["menu"], f["seat"], f["time"]),
            unsafe_allow_html=True,
        )
        st.info(f["tip"])
        st.caption("같은 날, 같은 이름이면 같은 운세가 나와요. 재미로만 봐 주세요!")


def tab_helper(day_items):
    st.markdown("#### 조리 도우미")
    st.caption("학년별 인원을 넣으면 필요한 재료 양과 배식 시간이 계산돼요.")
    c1, c2, c3 = st.columns(3)
    n1 = c1.number_input("1학년 인원", 0, 3000, 320, key="n1")
    n2 = c2.number_input("2학년 인원", 0, 3000, 310, key="n2")
    n3 = c3.number_input("3학년 인원", 0, 3000, 300, key="n3")
    c4, c5, c6 = st.columns(3)
    c4.number_input("배식 라인 수", 1, 10, 2, key="lines")
    c5.number_input("라인당 분당 인원", 1, 20, 8, key="rate")
    extra = c6.slider("여유분 (%)", 0, 15, 5)

    total = int(n1) + int(n2) + int(n3)
    factor = 1 + extra / 100.0
    st.metric("오늘 예상 식수", "%d명" % total)

    lines_md = ["| 항목 | 1인분 | 필요량 |", "|---|---|---|"]
    for label, per, unit in STANDARD:
        amount = per * total * factor / 1000.0
        big_unit = "kg" if unit == "g" else "L"
        lines_md.append("| %s | %d%s | **%.1f %s** |" % (label, per, unit, amount, big_unit))
    st.markdown("\n".join(lines_md))
    st.caption("기준량은 app.py의 STANDARD에서 학교에 맞게 고칠 수 있어요.")

    plan = make_plan([1, 2, 3], {1: int(n1), 2: int(n2), 3: int(n3)},
                     get_int("lines", 2), get_int("rate", 8))
    finish = plan[-1]["end"]
    st.metric("예상 배식 종료", fmt_time(finish),
              "총 %d분" % (finish - START_MIN))
    if finish - START_MIN > 60:
        st.warning("배식이 60분을 넘어요. 배식 라인을 늘리면 줄이 빨리 줄어요.")
    else:
        st.success("점심시간 안에 배식을 마칠 수 있어요.")


def main():
    now = datetime.now(KST)
    weekday = now.weekday()
    is_weekend = weekday >= 5
    today_idx = 0 if is_weekend else weekday

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="lz-hd"><div class="lz-sub">%s</div><h1>급식실 도우미</h1>'
        '<div class="lz-sub">%d월 %d일 %s요일 · %02d:%02d</div></div>'
        % (html.escape(SCHOOL_NAME), now.month, now.day, "월화수목금토일"[weekday],
           now.hour, now.minute),
        unsafe_allow_html=True,
    )

    t1, t2, t3, t4 = st.tabs(["급식·순서", "자리 현황", "급식 운세", "조리 도우미"])
    with t1:
        tab_menu(now, weekday, is_weekend, today_idx)
    with t2:
        tab_seats()
    with t3:
        tab_fortune(now, MENU[today_idx]["items"])
    with t4:
        tab_helper(MENU[today_idx]["items"])

    st.caption("맛있는 급식을 정성껏 준비해 주시는 급식 아주머니, 감사합니다.")


try:
    main()
except Exception as exc:  # 예상치 못한 오류도 화면에 안내만 표시
    st.error("앗, 문제가 생겼어요. 새로고침(F5) 해 주세요.")
    st.caption("오류 내용: %s" % exc)
