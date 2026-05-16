"""Lab results — save current session vitals+labs, fetch historical timeline."""
from __future__ import annotations
from database.connection import get_connection

# ── Field definitions (key = exact DB column name) ───────────────────────────

VITAL_FIELDS = [
    ("weight_kg",    "น้ำหนัก (kg)"),
    ("height_cm",    "ส่วนสูง (cm)"),
    ("bmi",          "BMI"),
    ("waist_cm",     "รอบเอว (cm)"),
    ("systolic_bp",  "SBP (mmHg)"),
    ("diastolic_bp", "DBP (mmHg)"),
    ("pulse_bpm",    "ชีพจร (bpm)"),
]

LAB_FIELDS = [
    ("fbs",          "FBS (mg/dL)"),
    ("hba1c",        "HbA1c (%)"),
    ("ldl",          "LDL (mg/dL)"),
    ("hdl",          "HDL (mg/dL)"),
    ("triglyceride", "Triglyceride (mg/dL)"),
    ("total_chol",   "Total Chol (mg/dL)"),
    ("creatinine",   "Creatinine (mg/dL)"),
    ("egfr",         "eGFR (mL/min)"),
    ("uric_acid",    "Uric Acid (mg/dL)"),
    ("sgpt_alt",     "ALT (U/L)"),
    ("sgot_ast",     "AST (U/L)"),
    ("wbc",          "WBC (×10³/μL)"),
    ("hb",           "Hgb (g/dL)"),
    ("platelet",     "PLT (×10³/μL)"),
]

# Normal ranges (lo, hi) — None means no bound on that side
RANGES: dict[str, tuple[float | None, float | None]] = {
    "fbs":          (70.0,  100.0),
    "hba1c":        (None,  6.5),
    "ldl":          (None,  100.0),
    "hdl":          (40.0,  None),
    "triglyceride": (None,  150.0),
    "total_chol":   (None,  200.0),
    "creatinine":   (0.6,   1.2),
    "egfr":         (60.0,  None),
    "uric_acid":    (None,  7.0),
    "sgpt_alt":     (None,  40.0),
    "sgot_ast":     (None,  40.0),
    "wbc":          (4.5,   11.0),
    "hb":           (12.0,  17.5),
    "platelet":     (150.0, 400.0),
    "bmi":          (18.5,  24.9),
    "systolic_bp":  (None,  130.0),
    "diastolic_bp": (None,  80.0),
}


class LabService:

    # ── save vitals (UPSERT — one row per patient per session) ────────────

    def save_vitals(self, patient_id: int, session_id: int, data: dict, user_id: int) -> None:
        if not data:
            return
        conn = get_connection()
        cols         = list(data.keys())
        placeholders = ", ".join("?" * len(cols))
        sets         = ", ".join(f"{c}=excluded.{c}" for c in cols)
        # params order must match: patient_id, session_id, user_id, then each data value
        values = [patient_id, session_id, user_id] + list(data.values())
        conn.execute(
            f"""
            INSERT INTO vitals (patient_id, session_id, recorded_by, {", ".join(cols)})
            VALUES (?, ?, ?, {placeholders})
            ON CONFLICT(session_id, patient_id) DO UPDATE SET
                updated_at = datetime('now','localtime'),
                {sets}
            """,
            values,
        )
        conn.commit()

    # ── save labs (UPSERT — one row per patient per session) ──────────────

    def save_labs(self, patient_id: int, session_id: int, data: dict, user_id: int) -> None:
        if not data:
            return
        conn = get_connection()
        cols         = list(data.keys())
        placeholders = ", ".join("?" * len(cols))
        sets         = ", ".join(f"{c}=excluded.{c}" for c in cols)
        values = [patient_id, session_id, user_id] + list(data.values())
        conn.execute(
            f"""
            INSERT INTO lab_results (patient_id, session_id, recorded_by, {", ".join(cols)})
            VALUES (?, ?, ?, {placeholders})
            ON CONFLICT(session_id, patient_id) DO UPDATE SET
                updated_at = datetime('now','localtime'),
                {sets}
            """,
            values,
        )
        conn.commit()

    # ── fetch ─────────────────────────────────────────────────────────────

    def get_vitals(self, patient_id: int, session_id: int) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM vitals WHERE patient_id=? AND session_id=?",
            (patient_id, session_id),
        ).fetchone()
        return dict(row) if row else {}

    def get_labs(self, patient_id: int, session_id: int) -> dict:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM lab_results WHERE patient_id=? AND session_id=?",
            (patient_id, session_id),
        ).fetchone()
        return dict(row) if row else {}

    # ── historical timeline ───────────────────────────────────────────────

    def get_timeline(self, patient_id: int, years: int = 3) -> list[dict]:
        """
        Return list of session snapshots (newest first, capped to `years` distinct
        calendar years) that have vitals or lab data for the patient.
        """
        conn = get_connection()
        sessions = conn.execute(
            """
            SELECT DISTINCT s.id, s.session_date, s.session_code
              FROM sessions s
              JOIN session_patients sp ON sp.session_id = s.id
             WHERE sp.patient_id = ?
               AND (
                     EXISTS (SELECT 1 FROM vitals     WHERE patient_id=? AND session_id=s.id)
                  OR EXISTS (SELECT 1 FROM lab_results WHERE patient_id=? AND session_id=s.id)
               )
             ORDER BY s.session_date DESC
            """,
            (patient_id, patient_id, patient_id),
        ).fetchall()

        result     = []
        seen_years: set[str] = set()
        for s in sessions:
            yr = (s["session_date"] or "")[:4]
            if yr and len(seen_years) >= years and yr not in seen_years:
                continue
            if yr:
                seen_years.add(yr)
            vitals = self.get_vitals(patient_id, s["id"])
            labs   = self.get_labs(patient_id, s["id"])
            if vitals or labs:
                result.append({
                    "session_id":   s["id"],
                    "session_date": s["session_date"],
                    "session_code": s["session_code"],
                    "vitals": vitals,
                    "labs":   labs,
                })
        return result

    # ── custom lab results ────────────────────────────────────────────────

    def get_custom_labs(self, patient_id: int, session_id: int) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM custom_lab_results "
            "WHERE patient_id=? AND session_id=? ORDER BY id",
            (patient_id, session_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def save_custom_lab(
        self, patient_id: int, session_id: int,
        test_name: str, value: str, unit: str, user_id: int,
    ) -> int:
        conn = get_connection()
        cur = conn.execute(
            "INSERT INTO custom_lab_results "
            "(session_id, patient_id, test_name, value, unit, recorded_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, patient_id, test_name.strip(), value.strip(), unit.strip(), user_id),
        )
        conn.commit()
        return cur.lastrowid

    def delete_custom_lab(self, custom_lab_id: int) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM custom_lab_results WHERE id=?", (custom_lab_id,))
        conn.commit()

    def clear_template_field(
        self, patient_id: int, session_id: int,
        field_name: str, table: str,
    ) -> None:
        """Set a single column to NULL in vitals or lab_results."""
        allowed_vitals = {k for k, _ in VITAL_FIELDS}
        allowed_labs   = {k for k, _ in LAB_FIELDS}
        if table == "vitals" and field_name not in allowed_vitals:
            raise ValueError(f"Unknown vitals field: {field_name}")
        if table == "lab_results" and field_name not in allowed_labs:
            raise ValueError(f"Unknown lab field: {field_name}")
        conn = get_connection()
        conn.execute(
            f"UPDATE {table} SET {field_name}=NULL "
            "WHERE patient_id=? AND session_id=?",
            (patient_id, session_id),
        )
        conn.commit()

    # ── delete vitals + labs for one patient in one session ──────────────

    def delete_session_data(self, patient_id: int, session_id: int) -> None:
        conn = get_connection()
        conn.execute(
            "DELETE FROM vitals WHERE patient_id=? AND session_id=?",
            (patient_id, session_id),
        )
        conn.execute(
            "DELETE FROM lab_results WHERE patient_id=? AND session_id=?",
            (patient_id, session_id),
        )
        conn.commit()

    # ── queue enriched with lab status ────────────────────────────────────

    def get_queue_with_lab_status(self, session_id: int) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT sp.queue_no, sp.status, sp.patient_id,
                   p.hn, p.first_name, p.last_name,
                   (SELECT COUNT(*) FROM vitals
                     WHERE patient_id=p.id AND session_id=?) > 0 AS has_vitals,
                   (SELECT COUNT(*) FROM lab_results
                     WHERE patient_id=p.id AND session_id=?) > 0 AS has_labs
              FROM session_patients sp
              JOIN patients p ON p.id = sp.patient_id
             WHERE sp.session_id = ?
               AND sp.status IN ('checked_in','done')
             ORDER BY sp.queue_no
            """,
            (session_id, session_id, session_id),
        ).fetchall()
        return [dict(r) for r in rows]
