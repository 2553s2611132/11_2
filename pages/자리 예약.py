
import streamlit as st
import sqlite3
from datetime import date, datetime
from pathlib import Path

st.set_page_config(
    page_title="급식실 자리 예약",
    page_icon="🍱",
    layout="centered"
)

DB_PATH = Path(__file__).parent / "cafeteria.db"


# 데이터베이스 초기화
def init_db():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                meal TEXT NOT NULL,
                student_id TEXT NOT NULL,
                nickname TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'waiting',
                created_at TEXT NOT NULL,
                UNIQUE(day, meal, student_id)
            )
        """)


def get_db():
    return sqlite3.connect(DB_PATH, timeout=10)


def get_reservations(day, meal):
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("""
            SELECT * FROM reservations
            WHERE day = ? AND meal = ?
            AND status IN ('waiting', 'called')
            ORDER BY id
        """, (day, meal)).fetchall()


def get_position(rows, reservation_id):
    waiting_number = 0
    for row in rows:
        if row["status"] == "called":
            if row["id"] == reservation_id:
                return 0
            continue

        waiting_number += 1
        if row["id"] == reservation_id:
            return waiting_number

    return None


try:
    init_db()
except sqlite3.Error:
    st.error("데이터베이스를 초기화하지 못했습니다. 다시 실행해 주세요.")
    st.stop()


# 화면
st.title("🍱 급식실 자리 예약")
st.caption("예약하고, 내 순번에 맞춰 입장하세요!")

with st.sidebar:
    st.header("예약 설정")
    selected_day = st.date_input(
        "이용 날짜",
        value=date.today(),
        min_value=date.today()
    )
    meal = st.selectbox(
        "급식 시간",
        ["점심 1차", "점심 2차", "점심 3차"]
    )
    menu = st.radio(
        "메뉴",
        ["자리 예약", "내 순번 확인", "대기 현황", "관리자"]
    )

day = selected_day.isoformat()
rows = get_reservations(day, meal)
waiting_rows = [r for r in rows if r["status"] == "waiting"]
called_rows = [r for r in rows if r["status"] == "called"]

col1, col2, col3 = st.columns(3)
col1.metric("예약 인원", len(rows))
col2.metric("대기 인원", len(waiting_rows))
col3.metric("호출 인원", len(called_rows))

st.divider()


# 1. 자리 예약
if menu == "자리 예약":
    st.subheader("🪑 자리 예약하기")

    with st.form("reserve_form"):
        student_id = st.text_input("학번 또는 고유 ID")
        nickname = st.text_input("별명")
        submit = st.form_submit_button(
            "예약하기",
            type="primary",
            use_container_width=True
        )

    if submit:
        student_id = student_id.strip()
        nickname = nickname.strip()

        if not student_id or not nickname:
            st.warning("학번과 별명을 모두 입력해 주세요.")
        elif len(student_id) > 40 or len(nickname) > 40:
            st.warning("각 입력은 40자 이내로 작성해 주세요.")
        else:
            try:
                with get_db() as conn:
                    existing = conn.execute("""
                        SELECT status FROM reservations
                        WHERE day = ? AND meal = ? AND student_id = ?
                    """, (day, meal, student_id)).fetchone()

                    if existing and existing[0] in ("waiting", "called"):
                        st.warning("이미 예약되어 있습니다.")
                    else:
                        conn.execute("""
                            INSERT INTO reservations
                            (day, meal, student_id, nickname,
                             status, created_at)
                            VALUES (?, ?, ?, ?, 'waiting', ?)
                            ON CONFLICT(day, meal, student_id)
                            DO UPDATE SET
                                nickname = excluded.nickname,
                                status = 'waiting',
                                created_at = excluded.created_at
                        """, (
                            day, meal, student_id, nickname,
                            datetime.now().isoformat(timespec="seconds")
                        ))
                        st.success("예약이 완료되었습니다!")
                        st.rerun()

            except sqlite3.Error:
                st.error("예약에 실패했습니다. 잠시 후 다시 시도해 주세요.")


# 2. 내 순번 확인 및 예약 취소
elif menu == "내 순번 확인":
    st.subheader("🔔 내 순번 확인")

    student_id = st.text_input("예약할 때 입력한 학번 또는 ID")

    if st.button("순번 확인", use_container_width=True):
        if not student_id.strip():
            st.warning("학번 또는 ID를 입력해 주세요.")
        else:
            with get_db() as conn:
                conn.row_factory = sqlite3.Row
                mine = conn.execute("""
                    SELECT * FROM reservations
                    WHERE day = ? AND meal = ? AND student_id = ?
                """, (day, meal, student_id.strip())).fetchone()

            current_rows = get_reservations(day, meal)

            if mine is None:
                st.info("예약 정보를 찾을 수 없습니다.")
            elif mine["status"] == "cancelled":
                st.warning("취소된 예약입니다.")
            elif mine["status"] == "served":
                st.success("이미 이용 완료된 예약입니다.")
            elif mine["status"] == "called":
                st.success("🔔 지금 입장할 차례입니다!")
            else:
                position = get_position(current_rows, mine["id"])
                st.success(f"현재 대기 순번: {position}번")
                st.info("대기 현황에서 순번을 다시 확인할 수 있습니다.")

            if mine and mine["status"] in ("waiting", "called"):
                if st.button("예약 취소"):
                    with get_db() as conn:
                        conn.execute("""
                            UPDATE reservations SET status = 'cancelled'
                            WHERE id = ?
                        """, (mine["id"],))
                    st.success("예약이 취소되었습니다.")
                    st.rerun()


# 3. 대기 현황
elif menu == "대기 현황":
    st.subheader("📋 대기 현황")
    st.caption("화면을 새로고침하면 최신 순번을 확인할 수 있습니다.")

    if not rows:
        st.info("현재 예약자가 없습니다.")
    else:
        for row in rows:
            if row["status"] == "called":
                st.success(f"🔔 {row['nickname']} — 입장 차례")
            else:
                position = get_position(rows, row["id"])
                st.write(f"🪑 {position}번 · {row['nickname']}")


# 4. 관리자
elif menu == "관리자":
    st.subheader("🔐 관리자 메뉴")

    try:
        password = st.secrets["ADMIN_PASSWORD"]
    except Exception:
        password = ""

    if not password:
        st.error(
            "관리자 비밀번호가 설정되지 않았습니다. "
            "Streamlit Secrets에 ADMIN_PASSWORD를 등록하세요."
        )
    else:
        entered = st.text_input("관리자 비밀번호", type="password")

        if entered == password:
            st.success("관리자 인증 완료")

            batch = st.number_input(
                "한 번에 호출할 인원",
                min_value=1,
                max_value=100,
                value=5
            )

            if st.button("다음 순번 호출", type="primary"):
                try:
                    with get_db() as conn:
                        next_rows = conn.execute("""
                            SELECT id FROM reservations
                            WHERE day = ? AND meal = ? AND status = 'waiting'
                            ORDER BY id LIMIT ?
                        """, (day, meal, int(batch))).fetchall()

                        if not next_rows:
                            st.info("호출할 대기자가 없습니다.")
                        else:
                            ids = [r[0] for r in next_rows]
                            conn.executemany("""
                                UPDATE reservations
                                SET status = 'called'
                                WHERE id = ?
                            """, [(i,) for i in ids])

                            st.success(
                                f"{len(ids)}명을 호출했습니다."
                            )
                            st.rerun()

                except sqlite3.Error:
                    st.error("호출 처리 중 오류가 발생했습니다.")

            if st.button("호출된 인원 이용 완료 처리"):
                with get_db() as conn:
                    conn.execute("""
                        UPDATE reservations SET status = 'served'
                        WHERE day = ? AND meal = ? AND status = 'called'
                    """, (day, meal))
                st.success("이용 완료 처리했습니다.")
                st.rerun()

            st.divider()
            st.markdown("#### 예약자 관리")

            for row in get_reservations(day, meal):
                a, b = st.columns([3, 1])
                a.write(f"{row['nickname']} ({row['student_id']})")
                if b.button("취소", key=f"cancel_{row['id']}"):
                    with get_db() as conn:
                        conn.execute("""
                            UPDATE reservations SET status = 'cancelled'
                            WHERE id = ?
                        """, (row["id"],))
                    st.rerun()

        elif entered:
            st.error("비밀번호가 올바르지 않습니다.")


st.divider()
st.caption("급식실 자리 예약 시스템")
