"""
Excel / CSV import service.

Column detection strategy
─────────────────────────
• Demographics  — matched by exact normalised name (see DEMO_MAP)
• Medical history — matched by HISTORY_MAP
• Historical labs — regex  <lab_base>_<YYYY>  e.g. fbs_2023, ldl_2024
  → auto-creates a session row (is_historical=1) for each year found

Upsert key priority: national_id → hn → create new patient
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

import pandas as pd

from database.connection import get_connection
from services.patient_service import PatientService
from utils.validators import normalise_date

# ── column name maps ───────────────────────────────────────────────────────

DEMO_MAP: dict[str, str] = {
    "national_id": "national_id", "nationalid": "national_id",
    "citizen_id": "national_id",  "id_card": "national_id",
    "hn": "hn",
    "first_name": "first_name",  "firstname": "first_name",
    "fname": "first_name",       "ชื่อ": "first_name",
    "last_name": "last_name",    "lastname": "last_name",
    "lname": "last_name",        "นามสกุล": "last_name",
    "dob": "date_of_birth",      "date_of_birth": "date_of_birth",
    "birthdate": "date_of_birth","วันเกิด": "date_of_birth",
    "gender": "gender",          "sex": "gender", "เพศ": "gender",
    "phone": "phone",            "tel": "phone",
    "telephone": "phone",        "mobile": "phone", "เบอร์โทร": "phone",
    "department": "department",  "dept": "department", "แผนก": "department",
}

HISTORY_MAP: dict[str, str] = {
    "conditions": "conditions",     "disease": "conditions",
    "underlying": "conditions",     "โรคประจำตัว": "conditions",
    "drug_allergies": "drug_allergies", "drug_allergy": "drug_allergies",
    "แพ้ยา": "drug_allergies",
    "food_allergies": "food_allergies", "food_allergy": "food_allergies",
    "แพ้อาหาร": "food_allergies",
    "medications": "medications",   "medication": "medications",
    "ยาประจำ": "medications",
    "is_smoker": "is_smoker",       "smoker": "is_smoker",
    "is_drinker": "is_drinker",     "drinker": "is_drinker",
}

LAB_MAP: dict[str, str] = {
    "fbs": "fbs",           "glucose": "fbs",
    "hba1c": "hba1c",
    "total_chol": "total_chol", "cholesterol": "total_chol", "chol": "total_chol",
    "hdl": "hdl",
    "ldl": "ldl",
    "triglyceride": "triglyceride", "tg": "triglyceride",
    "creatinine": "creatinine",     "cr": "creatinine",
    "bun": "bun",
    "uric_acid": "uric_acid",       "uric": "uric_acid",
    "egfr": "egfr",
    "sgot": "sgot_ast",     "ast": "sgot_ast",
    "sgpt": "sgpt_alt",     "alt": "sgpt_alt",
    "hb": "hb",             "hemoglobin": "hb",
    "hct": "hct",
    "wbc": "wbc",
    "platelet": "platelet",
    "tsh": "tsh",
}

GENDER_MAP: dict[str, str] = {
    "m": "M", "male": "M",   "ชาย": "M", "1": "M",
    "f": "F", "female": "F", "หญิง": "F", "2": "F",
}

_YEAR_RE = re.compile(r"^(.+?)_(\d{4})$")


# ── data classes ───────────────────────────────────────────────────────────

@dataclass
class RowPreview:
    row_num: int
    national_id: str = ""
    hn: str = ""
    full_name: str = ""
    status: str = "ok"      # "ok" | "error"
    is_new: bool = True
    message: str = ""


@dataclass
class ImportPreview:
    filepath: str
    total: int = 0
    valid: int = 0
    invalid: int = 0
    new_count: int = 0
    update_count: int = 0
    rows: list[RowPreview] = field(default_factory=list)
    _parsed: list[dict] = field(default_factory=list)   # internal use only


@dataclass
class ImportResult:
    total: int = 0
    new_patients: int = 0
    updated_patients: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)


# ── service ────────────────────────────────────────────────────────────────

class ImportService:
    def __init__(self) -> None:
        self._psvc = PatientService()

    # ── Step 1: parse & preview (no DB writes) ──────────────────────────

    def parse_file(self, filepath: str) -> ImportPreview:
        preview = ImportPreview(filepath=filepath)
        try:
            df = (
                pd.read_csv(filepath, dtype=str, keep_default_na=False)
                if filepath.lower().endswith(".csv")
                else pd.read_excel(filepath, dtype=str, keep_default_na=False)
            )
        except Exception as exc:
            preview.invalid = 1
            preview.rows.append(RowPreview(
                row_num=1, status="error",
                message=f"ไม่สามารถอ่านไฟล์: {exc}",
            ))
            return preview

        df.columns = [
            str(c).strip().lower().replace(" ", "_") for c in df.columns
        ]
        preview.total = len(df)

        for idx, row in df.iterrows():
            row_num = int(idx) + 2          # Excel row 1 = header
            rp      = RowPreview(row_num=row_num)
            try:
                parsed = self._parse_row(row, list(df.columns))

                first = parsed["demo"].get("first_name", "")
                last  = parsed["demo"].get("last_name", "")
                nid   = parsed["demo"].get("national_id", "")
                hn    = parsed["demo"].get("hn", "")

                rp.national_id = nid
                rp.hn          = hn
                rp.full_name   = f"{first} {last}".strip()

                if not rp.full_name:
                    raise ValueError("ไม่มีชื่อ-นามสกุล")

                existing = None
                if nid:
                    existing = self._psvc.get_by_national_id(nid)
                if not existing and hn:
                    existing = self._psvc.get_by_hn(hn)
                if not existing and first and last:
                    dob = parsed["demo"].get("date_of_birth")
                    existing = self._psvc.get_by_name_dob(first, last, dob)

                rp.is_new = existing is None
                if rp.is_new:
                    preview.new_count += 1
                else:
                    preview.update_count += 1
                    rp.hn = existing["hn"]   # show real HN

                preview.valid += 1
                parsed["_existing_id"] = existing["id"] if existing else None
                preview._parsed.append(parsed)

            except Exception as exc:
                rp.status  = "error"
                rp.message = str(exc)
                preview.invalid += 1

            preview.rows.append(rp)

        return preview

    def _parse_row(self, row: pd.Series, cols: list[str]) -> dict:
        demo: dict    = {}
        history: dict = {}
        labs: dict    = {}          # { year: { lab_field: value } }

        for col in cols:
            raw = str(row.get(col, "")).strip()
            if not raw:
                continue

            # Year-suffixed lab column  e.g. fbs_2023 (CE) or fbs_2566 (BE)
            m = _YEAR_RE.match(col)
            if m:
                base, year = m.group(1), int(m.group(2))
                if year >= 2500:   # Buddhist Era → convert to CE
                    year -= 543
                db_field = LAB_MAP.get(base)
                if db_field:
                    try:
                        labs.setdefault(year, {})[db_field] = float(raw)
                    except ValueError:
                        pass
                continue

            if col in DEMO_MAP:
                db_field = DEMO_MAP[col]
                if db_field == "date_of_birth":
                    raw = normalise_date(raw) or raw
                elif db_field == "gender":
                    raw = GENDER_MAP.get(raw.lower(), raw.upper()[:1])
                demo[db_field] = raw
                continue

            if col in HISTORY_MAP:
                db_field = HISTORY_MAP[col]
                if db_field in ("is_smoker", "is_drinker"):
                    raw = 1 if raw.lower() in ("1", "yes", "true", "ใช่", "มี") else 0
                history[db_field] = raw

        return {"demo": demo, "history": history, "labs": labs}

    # ── Step 2: execute confirmed import ────────────────────────────────

    def execute_import(
        self,
        preview: ImportPreview,
        session_id: int | None,
        user_id: int,
    ) -> ImportResult:
        result  = ImportResult(total=preview.valid)
        ok_rows = [r for r in preview.rows if r.status == "ok"]

        for rp, parsed in zip(ok_rows, preview._parsed):
            try:
                patient, is_new = self._psvc.upsert(parsed["demo"], user_id)

                if parsed.get("history"):
                    self._psvc.upsert_medical_history(
                        patient["id"], parsed["history"], user_id
                    )
                if parsed.get("labs"):
                    self._upsert_historical_labs(
                        patient["id"], parsed["labs"], user_id
                    )
                if session_id:
                    self._psvc.enrol(patient["id"], session_id, user_id)

                if is_new:
                    result.new_patients += 1
                else:
                    result.updated_patients += 1

            except Exception as exc:
                result.errors += 1
                result.error_details.append(
                    f"แถว {rp.row_num} ({rp.full_name}): {exc}"
                )

        return result

    # ── Helpers ──────────────────────────────────────────────────────────

    def _upsert_historical_labs(
        self, patient_id: int, labs_by_year: dict, user_id: int
    ) -> None:
        conn = get_connection()
        for year, lab_data in labs_by_year.items():
            code = f"HIST-{year}"
            row  = conn.execute(
                "SELECT id FROM sessions WHERE session_code = ?", (code,)
            ).fetchone()

            if row:
                sid = row["id"]
            else:
                be_year = year + 543
                cur = conn.execute(
                    "INSERT INTO sessions "
                    "(session_code, session_name, session_date, is_historical, is_active) "
                    "VALUES (?, ?, ?, 1, 0)",
                    (code, f"ข้อมูลย้อนหลัง {be_year} (พ.ศ.)", f"{year}-01-01"),
                )
                sid = cur.lastrowid

            fields     = list(lab_data.keys())
            vals       = list(lab_data.values())
            set_clause = ", ".join(f"{f} = ?" for f in fields)

            if conn.execute(
                "SELECT id FROM lab_results WHERE session_id = ? AND patient_id = ?",
                (sid, patient_id),
            ).fetchone():
                conn.execute(
                    f"UPDATE lab_results SET {set_clause}, recorded_by = ? "
                    f"WHERE session_id = ? AND patient_id = ?",
                    (*vals, user_id, sid, patient_id),
                )
            else:
                col_ph = ", ".join("?" * len(fields))
                conn.execute(
                    f"INSERT INTO lab_results "
                    f"(session_id, patient_id, {', '.join(fields)}, recorded_by) "
                    f"VALUES (?, ?, {col_ph}, ?)",
                    (sid, patient_id, *vals, user_id),
                )

        conn.commit()
