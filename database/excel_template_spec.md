# Excel Import Template Specification — BPK1 MOBILE UNIT

## Sheet 1 — Patient Demographics & Medical History

| Excel Column Header | DB Field | Required | Notes |
|---|---|---|---|
| `national_id` | `patients.national_id` | Yes* | 13-digit Thai ID. Used as upsert key. |
| `hn` | `patients.hn` | Yes* | Alternative upsert key if no national_id |
| `first_name` | `patients.first_name` | Yes | |
| `last_name` | `patients.last_name` | Yes | |
| `dob` | `patients.date_of_birth` | No | YYYY-MM-DD or DD/MM/YYYY (CE) or DD/MM/YYYY (BE พ.ศ.) |
| `gender` | `patients.gender` | No | M / F / Other  หรือ  ชาย / หญิง |
| `phone` | `patients.phone` | No | |
| `department` | `patients.department` | No | Company dept / แผนก |
| `conditions` | `patient_medical_history.conditions` | No | เช่น "HT, DM" |
| `drug_allergies` | `patient_medical_history.drug_allergies` | No | |
| `food_allergies` | `patient_medical_history.food_allergies` | No | |
| `medications` | `patient_medical_history.medications` | No | |
| `is_smoker` | `patient_medical_history.is_smoker` | No | 1/0 หรือ Yes/No |
| `is_drinker` | `patient_medical_history.is_drinker` | No | 1/0 หรือ Yes/No |

*At least one of `national_id` or `hn` is required.

---

## Sheet 2 (or additional columns) — Historical Lab Results

Year-suffixed columns map to auto-created historical sessions.
**รองรับทั้งปี ค.ศ. และ พ.ศ. (BE ≥ 2500 จะแปลงเป็น CE อัตโนมัติ)**

| Excel Column Header (พ.ศ.) | Excel Column Header (ค.ศ.) | DB Field | Session auto-created |
|---|---|---|---|
| `fbs_2566` | `fbs_2023` | `lab_results.fbs` | "ข้อมูลย้อนหลัง 2566 (พ.ศ.)" |
| `hba1c_2566` | `hba1c_2023` | `lab_results.hba1c` | same |
| `total_chol_2566` | `total_chol_2023` | `lab_results.total_chol` | same |
| `hdl_2566` | `hdl_2023` | `lab_results.hdl` | same |
| `ldl_2566` | `ldl_2023` | `lab_results.ldl` | same |
| `triglyceride_2566` | `triglyceride_2023` | `lab_results.triglyceride` | same |
| `creatinine_2566` | `creatinine_2023` | `lab_results.creatinine` | same |
| `fbs_2567` | `fbs_2024` | `lab_results.fbs` | "ข้อมูลย้อนหลัง 2567 (พ.ศ.)" |
| `hba1c_2567` | `hba1c_2024` | `lab_results.hba1c` | same |
| *(same pattern for all lab fields)* | | | |

### Supported Lab Fields (base names)

`fbs` · `hba1c` · `total_chol` / `cholesterol` / `chol` · `hdl` · `ldl` ·
`triglyceride` / `tg` · `creatinine` / `cr` · `bun` · `uric_acid` / `uric` ·
`egfr` · `sgot` / `ast` · `sgpt` / `alt` · `hb` / `hemoglobin` · `hct` ·
`wbc` · `platelet` · `tsh`

---

### Import Logic (Pandas parsing flow)

```
1. อ่านไฟล์ Excel / CSV ด้วย pandas
2. Normalize column headers → lowercase, strip spaces
3. แบ่งคอลัมน์เป็น 3 กลุ่ม:
      - demographic_cols   (ไม่มีปี suffix)
      - history_cols       (ข้อมูลสุขภาพ)
      - lab_cols           (regex: r'^([a-z_]+)_(\d{4})$')
         BE year (>= 2500) จะถูกแปลง CE = BE - 543 ก่อนบันทึก
4. For each row:
   a. Resolve patient by national_id → HN (upsert, auto-HN ถ้าใหม่)
   b. Upsert patient_medical_history
   c. For each year found in lab_cols:
         - Find or create session  is_historical=1, session_date=YYYY-01-01
         - Upsert lab_results row for (session_id, patient_id)
5. Collect per-row errors → แสดง summary dialog
6. User confirms → commit; cancel → rollback
```

### Export (Session Excel)

ไฟล์ Excel ที่ export จะมี 3 sheets:
- **Patients** — ข้อมูลผู้ป่วย + สถานะคิว
- **Vitals** — สัญญาณชีพ
- **Labs** — ผลตรวจเลือด (pivot: 1 row per patient, 1 col per test)
