from database.connection import get_connection
from utils.hn_generator import generate_hn


class PatientService:

    # ── Search / lookup ────────────────────────────────────────────────

    def search(self, term: str = "", session_id: int | None = None) -> list[dict]:
        conn = get_connection()
        like = f"%{term}%"
        if session_id is not None:
            rows = conn.execute("""
                SELECT p.*,
                       sp.status        AS session_status,
                       sp.queue_no,
                       sp.checked_in_at
                FROM patients p
                LEFT JOIN session_patients sp
                    ON sp.patient_id = p.id AND sp.session_id = ?
                WHERE p.hn LIKE ? OR p.first_name LIKE ?
                   OR p.last_name LIKE ? OR p.national_id LIKE ?
                ORDER BY p.last_name, p.first_name
                LIMIT 500
            """, (session_id, like, like, like, like)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM patients
                WHERE hn LIKE ? OR first_name LIKE ?
                   OR last_name LIKE ? OR national_id LIKE ?
                ORDER BY last_name, first_name
                LIMIT 500
            """, (like, like, like, like)).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, pid: int) -> dict | None:
        r = get_connection().execute(
            "SELECT * FROM patients WHERE id = ?", (pid,)
        ).fetchone()
        return dict(r) if r else None

    def get_by_national_id(self, nid: str) -> dict | None:
        r = get_connection().execute(
            "SELECT * FROM patients WHERE national_id = ?", (nid.strip(),)
        ).fetchone()
        return dict(r) if r else None

    def get_by_hn(self, hn: str) -> dict | None:
        r = get_connection().execute(
            "SELECT * FROM patients WHERE hn = ?", (hn.strip(),)
        ).fetchone()
        return dict(r) if r else None

    # ── Write ──────────────────────────────────────────────────────────

    def create(self, data: dict, user_id: int) -> dict:
        hn   = generate_hn()
        conn = get_connection()
        conn.execute("""
            INSERT INTO patients
                (hn, national_id, first_name, last_name,
                 date_of_birth, gender, phone, department, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hn,
            data.get("national_id") or None,
            data["first_name"].strip(),
            data["last_name"].strip(),
            data.get("date_of_birth") or None,
            data.get("gender") or None,
            data.get("phone") or None,
            data.get("department") or None,
            user_id,
        ))
        conn.commit()
        return self.get_by_hn(hn)

    def delete(self, patient_id: int) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()

    def update(self, patient_id: int, data: dict) -> None:
        conn   = get_connection()
        fields = ["first_name", "last_name", "national_id",
                  "date_of_birth", "gender", "phone", "department"]
        updates = {f: data[f] for f in fields if f in data and data[f] is not None}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE patients SET {set_clause} WHERE id = ?",
            (*updates.values(), patient_id),
        )
        conn.commit()

    def upsert(self, data: dict, user_id: int) -> tuple[dict, bool]:
        """Returns (patient_dict, is_new)."""
        existing = None
        nid = (data.get("national_id") or "").strip()
        hn  = (data.get("hn") or "").strip()
        if nid:
            existing = self.get_by_national_id(nid)
        if not existing and hn:
            existing = self.get_by_hn(hn)
        if existing:
            self.update(existing["id"], data)
            return self.get_by_hn(existing["hn"]), False
        return self.create(data, user_id), True

    # ── Session enrolment ──────────────────────────────────────────────

    def enrol(self, patient_id: int, session_id: int, user_id: int) -> bool:
        """Enrol patient into session. Returns False if already enrolled."""
        conn = get_connection()
        if conn.execute(
            "SELECT id FROM session_patients WHERE session_id = ? AND patient_id = ?",
            (session_id, patient_id),
        ).fetchone():
            return False

        next_q = conn.execute(
            "SELECT COALESCE(MAX(queue_no), 0) + 1 AS nxt "
            "FROM session_patients WHERE session_id = ?",
            (session_id,),
        ).fetchone()["nxt"]

        conn.execute(
            "INSERT INTO session_patients (session_id, patient_id, queue_no) VALUES (?, ?, ?)",
            (session_id, patient_id, next_q),
        )
        conn.commit()
        return True

    # ── Medical history ────────────────────────────────────────────────

    def get_medical_history(self, patient_id: int) -> dict | None:
        r = get_connection().execute(
            "SELECT * FROM patient_medical_history WHERE patient_id = ?",
            (patient_id,),
        ).fetchone()
        return dict(r) if r else None

    def upsert_medical_history(self, patient_id: int, data: dict, user_id: int) -> None:
        conn    = get_connection()
        fields  = ["conditions", "drug_allergies", "food_allergies",
                   "medications", "is_smoker", "is_drinker", "notes"]
        existing = self.get_medical_history(patient_id)
        if existing:
            updates = {f: data[f] for f in fields if f in data}
            if not updates:
                return
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE patient_medical_history "
                f"SET {set_clause}, updated_by = ?, "
                f"updated_at = datetime('now','localtime') "
                f"WHERE patient_id = ?",
                (*updates.values(), user_id, patient_id),
            )
        else:
            conn.execute("""
                INSERT INTO patient_medical_history
                    (patient_id, conditions, drug_allergies, food_allergies,
                     medications, is_smoker, is_drinker, notes, updated_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                data.get("conditions"),       data.get("drug_allergies"),
                data.get("food_allergies"),   data.get("medications"),
                int(bool(data.get("is_smoker"))),
                int(bool(data.get("is_drinker"))),
                data.get("notes"),            user_id,
            ))
        conn.commit()
