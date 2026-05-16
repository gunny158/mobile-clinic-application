"""Vaccination records — save/fetch/delete per-session vaccine administration."""
from __future__ import annotations
from database.connection import get_connection

COMMON_VACCINES = [
    "ไข้หวัดใหญ่ (Influenza)",
    "COVID-19",
    "ตับอักเสบบี (Hepatitis B)",
    "บาดทะยัก (Td/Tdap)",
    "ปอดอักเสบ (PCV)",
    "ไข้เลือดออก (Dengue)",
]

ROUTES = ["IM (กล้ามเนื้อ)", "SC (ใต้ผิวหนัง)", "ID (ในผิวหนัง)", "Oral (กิน)"]

SITES = [
    "ต้นแขนซ้าย",
    "ต้นแขนขวา",
    "ต้นขาซ้าย",
    "ต้นขาขวา",
    "สะโพก",
]

DOSE_OPTIONS = ["เข็มที่ 1", "เข็มที่ 2", "เข็มที่ 3", "Booster", "ไม่ระบุ"]


class VaccinationService:

    def get_vaccinations(self, patient_id: int, session_id: int) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT v.*, u.full_name AS given_by_name
              FROM vaccinations v
              LEFT JOIN users u ON u.id = v.given_by
             WHERE v.patient_id = ? AND v.session_id = ?
             ORDER BY v.id
            """,
            (patient_id, session_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def add_vaccination(
        self,
        patient_id: int,
        session_id: int,
        vaccine_name: str,
        dose_no: str,
        lot_number: str,
        route: str,
        site: str,
        notes: str,
        user_id: int,
    ) -> int:
        conn = get_connection()
        cur = conn.execute(
            """
            INSERT INTO vaccinations
                (session_id, patient_id, vaccine_name, dose_no, lot_number,
                 route, site, notes, given_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, patient_id,
             vaccine_name.strip(), dose_no.strip(), lot_number.strip(),
             route.strip(), site.strip(), notes.strip(), user_id),
        )
        conn.commit()
        return cur.lastrowid

    def delete_vaccination(self, vax_id: int) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM vaccinations WHERE id = ?", (vax_id,))
        conn.commit()

    def get_queue_with_vax_status(self, session_id: int) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT sp.queue_no, sp.status, sp.patient_id,
                   p.hn, p.first_name, p.last_name,
                   (SELECT COUNT(*) FROM vaccinations
                     WHERE patient_id = p.id AND session_id = ?) > 0 AS has_vax
              FROM session_patients sp
              JOIN patients p ON p.id = sp.patient_id
             WHERE sp.session_id = ?
               AND sp.status IN ('checked_in', 'done')
             ORDER BY sp.queue_no
            """,
            (session_id, session_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_history(self, patient_id: int) -> list[dict]:
        """All vaccine records for this patient across sessions, newest first."""
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT v.*, s.session_date, s.session_name, u.full_name AS given_by_name
              FROM vaccinations v
              JOIN sessions s ON s.id = v.session_id
              LEFT JOIN users u ON u.id = v.given_by
             WHERE v.patient_id = ?
             ORDER BY s.session_date DESC, v.id DESC
            """,
            (patient_id,),
        ).fetchall()
        return [dict(r) for r in rows]
