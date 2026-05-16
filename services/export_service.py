"""Export and backup utilities."""
from __future__ import annotations
import os
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import EXPORTS_DIR, BACKUPS_DIR, DB_PATH
from database.connection import get_connection

EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


class ExportService:

    # ── Session export ────────────────────────────────────────────────────

    def export_session_excel(self, session_id: int) -> Path:
        """Export all patients + vitals + labs for a session to Excel."""
        conn = get_connection()
        now  = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_row = conn.execute(
            "SELECT session_code, session_date FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        code = session_row["session_code"] if session_row else str(session_id)

        filename = EXPORTS_DIR / f"session_{code}_{now}.xlsx"

        # Patients + queue status
        patients = conn.execute(
            """
            SELECT sp.queue_no, sp.status, sp.checked_in_at,
                   p.hn, p.first_name, p.last_name, p.national_id,
                   p.gender, p.date_of_birth, p.phone, p.department,
                   mh.conditions, mh.drug_allergies, mh.food_allergies,
                   mh.medications, mh.is_smoker, mh.is_drinker
              FROM session_patients sp
              JOIN patients p ON p.id = sp.patient_id
              LEFT JOIN patient_medical_history mh ON mh.patient_id = p.id
             WHERE sp.session_id = ?
             ORDER BY sp.queue_no
            """,
            (session_id,),
        ).fetchall()
        df_patients = pd.DataFrame([dict(r) for r in patients])

        _ATTEND = {
            "checked_in": "มาตรวจแล้ว",
            "done":       "มาตรวจแล้ว",
            "pending":    "ยังไม่มาตรวจ",
            "absent":     "ยังไม่มาตรวจ",
        }
        if not df_patients.empty:
            attendance = df_patients["status"].map(_ATTEND).fillna("ยังไม่มาตรวจ")
            ins = df_patients.columns.get_loc("last_name") + 1
            df_patients.insert(ins, "สถานะการมา", attendance)

        # Vitals
        vitals = conn.execute(
            """
            SELECT p.hn, v.*
              FROM vitals v
              JOIN patients p ON p.id = v.patient_id
             WHERE v.session_id = ?
            """,
            (session_id,),
        ).fetchall()
        df_vitals = pd.DataFrame([dict(r) for r in vitals]) if vitals else pd.DataFrame()

        # Standard labs (wide format — one column per test)
        labs = conn.execute(
            """
            SELECT p.hn, lr.fbs, lr.hba1c, lr.total_chol, lr.hdl, lr.ldl,
                   lr.triglyceride, lr.creatinine, lr.bun, lr.uric_acid,
                   lr.egfr, lr.sgot_ast, lr.sgpt_alt, lr.hb, lr.hct,
                   lr.wbc, lr.platelet, lr.ua_glucose, lr.ua_protein,
                   lr.ua_blood, lr.tsh
              FROM lab_results lr
              JOIN patients p ON p.id = lr.patient_id
             WHERE lr.session_id = ?
            """,
            (session_id,),
        ).fetchall()
        df_labs = pd.DataFrame([dict(r) for r in labs]) if labs else pd.DataFrame()

        # Custom labs (pivot long → wide)
        custom_labs = conn.execute(
            """
            SELECT p.hn, clr.test_name, clr.value
              FROM custom_lab_results clr
              JOIN patients p ON p.id = clr.patient_id
             WHERE clr.session_id = ?
            """,
            (session_id,),
        ).fetchall()
        if custom_labs:
            df_custom_long = pd.DataFrame([dict(r) for r in custom_labs])
            df_custom = df_custom_long.pivot_table(
                index="hn", columns="test_name", values="value", aggfunc="first"
            ).reset_index()
            df_custom.columns.name = None
        else:
            df_custom = pd.DataFrame()

        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            if not df_patients.empty:
                df_patients.to_excel(writer, sheet_name="Patients", index=False)
            if not df_vitals.empty:
                df_vitals.to_excel(writer, sheet_name="Vitals", index=False)
            if not df_labs.empty:
                df_labs.to_excel(writer, sheet_name="Labs", index=False)
            if not df_custom.empty:
                df_custom.to_excel(writer, sheet_name="Custom Labs", index=False)

        return filename

    # ── Full patient export ───────────────────────────────────────────────

    def export_all_patients(self) -> Path:
        conn = get_connection()
        now  = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = EXPORTS_DIR / f"all_patients_{now}.xlsx"

        patients = conn.execute(
            """
            SELECT p.hn, p.first_name, p.last_name, p.national_id,
                   p.gender, p.date_of_birth, p.phone, p.department,
                   mh.conditions, mh.drug_allergies, mh.food_allergies,
                   mh.medications, mh.is_smoker, mh.is_drinker
              FROM patients p
              LEFT JOIN patient_medical_history mh ON mh.patient_id = p.id
             ORDER BY p.hn
            """
        ).fetchall()
        df = pd.DataFrame([dict(r) for r in patients])
        df.to_excel(filename, index=False, engine="openpyxl")
        return filename

    # ── DB backup ─────────────────────────────────────────────────────────

    def backup_database(self) -> Path:
        now      = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest     = BACKUPS_DIR / f"clinic_backup_{now}.db"
        shutil.copy2(DB_PATH, dest)
        return dest

    # ── Restore DB ────────────────────────────────────────────────────────

    def restore_database(self, backup_path: str) -> None:
        """Replace current DB with a backup. App must be restarted afterward."""
        import database.connection as _db_module
        if _db_module._conn is not None:
            _db_module._conn.close()
            _db_module._conn = None
        shutil.copy2(backup_path, DB_PATH)

    # ── List backups ──────────────────────────────────────────────────────

    def list_backups(self) -> list[Path]:
        return sorted(BACKUPS_DIR.glob("clinic_backup_*.db"), reverse=True)

    def list_exports(self) -> list[Path]:
        return sorted(EXPORTS_DIR.glob("*.xlsx"), reverse=True)
