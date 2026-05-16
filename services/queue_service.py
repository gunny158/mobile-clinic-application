"""
Queue management and barcode check-in logic.

Scan identifier priority:
  HN26010001  →  normalised to  HN-2601-0001  (10-char, no dashes)
  HN-2601-0001  →  used directly
  1234567890123  →  treated as national ID (13 digits)
"""
from database.connection import get_connection
from services.patient_service import PatientService

OK               = "ok"
NOT_FOUND        = "not_found"
NOT_ENROLLED     = "not_enrolled"
ALREADY_DONE     = "already_done"
ALREADY_COMPLETE = "already_complete"


class QueueService:
    def __init__(self) -> None:
        self._psvc = PatientService()

    # ── Shared identifier resolver (read-only) ──────────────────────────

    def lookup(self, identifier: str, session_id: int) -> dict:
        """
        Resolve HN / national_id → patient + session_patients row (no DB write).
        Returns { status, patient, sp }.
        """
        clean = identifier.strip().upper().replace(" ", "")
        if (clean.startswith("HN") and "-" not in clean
                and len(clean) == 10 and clean[2:].isdigit()):
            clean = f"HN-{clean[2:6]}-{clean[6:]}"

        patient = None
        if clean.startswith("HN"):
            patient = self._psvc.get_by_hn(clean)
        if not patient and clean.isdigit() and len(clean) == 13:
            patient = self._psvc.get_by_national_id(clean)

        if not patient:
            return {"status": NOT_FOUND, "patient": None, "sp": None}

        conn = get_connection()
        sp = conn.execute(
            "SELECT * FROM session_patients WHERE session_id = ? AND patient_id = ?",
            (session_id, patient["id"]),
        ).fetchone()

        if not sp:
            return {"status": NOT_ENROLLED, "patient": patient, "sp": None}

        return {"status": OK, "patient": patient, "sp": dict(sp)}

    # ── Check-in via barcode scan ───────────────────────────────────────

    def check_in(self, identifier: str, session_id: int, user_id: int) -> dict:
        """
        Returns dict:
          { status: str, patient: dict | None, checked_in_at: str | None }
        """
        clean = identifier.strip().upper().replace(" ", "")

        # Normalise compact HN  HN26010001 → HN-2601-0001
        if (clean.startswith("HN") and "-" not in clean
                and len(clean) == 10 and clean[2:].isdigit()):
            clean = f"HN-{clean[2:6]}-{clean[6:]}"

        patient = None
        if clean.startswith("HN"):
            patient = self._psvc.get_by_hn(clean)
        if not patient and clean.isdigit() and len(clean) == 13:
            patient = self._psvc.get_by_national_id(clean)

        if not patient:
            return {"status": NOT_FOUND, "patient": None, "checked_in_at": None}

        conn = get_connection()
        sp = conn.execute(
            "SELECT * FROM session_patients WHERE session_id = ? AND patient_id = ?",
            (session_id, patient["id"]),
        ).fetchone()

        if not sp:
            return {"status": NOT_ENROLLED, "patient": patient, "checked_in_at": None}

        if sp["status"] in ("checked_in", "done"):
            return {"status": ALREADY_DONE, "patient": patient,
                    "checked_in_at": sp["checked_in_at"]}

        conn.execute("""
            UPDATE session_patients
               SET status       = 'checked_in',
                   checked_in_at = datetime('now','localtime'),
                   checked_in_by = ?
             WHERE session_id = ? AND patient_id = ?
        """, (user_id, session_id, patient["id"]))
        conn.commit()
        return {"status": OK, "patient": patient, "checked_in_at": None}

    # ── Scan-to-complete via barcode ────────────────────────────────────

    def scan_complete(self, identifier: str, session_id: int, user_id: int) -> dict:
        """
        Scan barcode → mark patient as 'done' (เสร็จสิ้น) regardless of prior status.
        Returns { status, patient, sp }.
        """
        result = self.lookup(identifier, session_id)
        if result["status"] != OK:
            return result

        patient = result["patient"]
        sp      = result["sp"]

        if sp["status"] == "done":
            return {"status": ALREADY_COMPLETE, "patient": patient, "sp": sp}

        conn = get_connection()
        conn.execute(
            "UPDATE session_patients SET status = 'done' "
            "WHERE session_id = ? AND patient_id = ?",
            (session_id, patient["id"]),
        )
        conn.commit()
        return {"status": OK, "patient": patient, "sp": sp}

    # ── Manual status change ────────────────────────────────────────────

    def update_status(
        self, patient_id: int, session_id: int, new_status: str, user_id: int
    ) -> None:
        conn = get_connection()
        if new_status == "checked_in":
            conn.execute("""
                UPDATE session_patients
                   SET status = ?,
                       checked_in_at = datetime('now','localtime'),
                       checked_in_by = ?
                 WHERE patient_id = ? AND session_id = ?
            """, (new_status, user_id, patient_id, session_id))
        else:
            conn.execute(
                "UPDATE session_patients SET status = ? WHERE patient_id = ? AND session_id = ?",
                (new_status, patient_id, session_id),
            )
        conn.commit()

    # ── Queries ────────────────────────────────────────────────────────

    def get_queue(self, session_id: int, filter_status: str = "all") -> list[dict]:
        conn   = get_connection()
        sql    = """
            SELECT sp.queue_no, sp.status, sp.checked_in_at,
                   p.id AS patient_id, p.hn,
                   p.first_name, p.last_name, p.national_id,
                   p.date_of_birth, p.gender, p.department, p.phone, p.created_at
              FROM session_patients sp
              JOIN patients p ON p.id = sp.patient_id
             WHERE sp.session_id = ?
        """
        params: list = [session_id]
        if filter_status != "all":
            sql += " AND sp.status = ?"
            params.append(filter_status)
        sql += " ORDER BY sp.queue_no"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def get_stats(self, session_id: int) -> dict:
        conn = get_connection()
        rows = conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM session_patients "
            "WHERE session_id = ? GROUP BY status",
            (session_id,),
        ).fetchall()
        s = {"pending": 0, "checked_in": 0, "done": 0, "absent": 0}
        for r in rows:
            s[r["status"]] = r["cnt"]
        s["all"] = sum(s.values())
        return s
