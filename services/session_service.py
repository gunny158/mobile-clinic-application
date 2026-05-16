from datetime import date
from database.connection import get_connection


class SessionService:

    def get_all_sessions(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM sessions WHERE is_historical = 0 ORDER BY session_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_active_sessions(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM sessions WHERE is_active = 1 AND is_historical = 0 "
            "ORDER BY session_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_session_stats(self, session_id: int) -> dict:
        conn = get_connection()
        rows = conn.execute(
            """SELECT status, COUNT(*) AS cnt
               FROM session_patients
               WHERE session_id = ?
               GROUP BY status""",
            (session_id,),
        ).fetchall()
        stats = {"pending": 0, "checked_in": 0, "done": 0, "absent": 0}
        for row in rows:
            stats[row["status"]] = row["cnt"]
        stats["total"] = sum(stats.values())
        return stats

    def get_patients(self, session_id: int) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            """SELECT
                   sp.queue_no, sp.status, sp.checked_in_at,
                   p.hn, p.first_name, p.last_name, p.national_id, p.phone
               FROM session_patients sp
               JOIN patients p ON p.id = sp.patient_id
               WHERE sp.session_id = ?
               ORDER BY sp.queue_no""",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: int) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()

    def create_session(
        self, name: str, location: str, session_date: str, created_by: int
    ) -> dict:
        conn = get_connection()
        year = session_date[:4]
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM sessions WHERE session_code LIKE ?",
            (f"SS-{year}-%",),
        ).fetchone()
        code = f"SS-{year}-{row['cnt'] + 1:03d}"

        cur = conn.execute(
            """INSERT INTO sessions (session_code, session_name, location, session_date, created_by)
               VALUES (?, ?, ?, ?, ?)""",
            (code, name, location, session_date, created_by),
        )
        conn.commit()
        return dict(
            conn.execute("SELECT * FROM sessions WHERE id = ?", (cur.lastrowid,)).fetchone()
        )
