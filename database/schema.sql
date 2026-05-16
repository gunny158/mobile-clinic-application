-- =============================================================
-- Mobile Clinic Database Schema  v1.2
-- SQLite 3 — Offline-first, all datetime stored as ISO-8601 text
-- =============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------
-- 1. USERS  (authentication & role-based access)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,            -- bcrypt hash
    full_name     TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user'
                          CHECK (role IN ('admin', 'user')),
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    last_login    TEXT
);

-- -------------------------------------------------------------
-- 2. SCREENING SESSIONS
--    One row per off-site event (can also be an auto-created
--    "Historical Import" session for past-year data).
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_code  TEXT    NOT NULL UNIQUE,   -- e.g. "SS-2568-001"
    session_name  TEXT    NOT NULL,          -- e.g. "ตรวจสุขภาพ ABC 2568-01"
    location      TEXT,
    session_date  TEXT    NOT NULL,          -- YYYY-MM-DD
    is_historical INTEGER NOT NULL DEFAULT 0, -- 1 = auto-created for imported past data
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    created_by    INTEGER REFERENCES users(id)
);

-- -------------------------------------------------------------
-- 3. PATIENTS  (master registry)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    hn            TEXT    NOT NULL UNIQUE,   -- "HN-2601-0042"
    national_id   TEXT    UNIQUE,            -- 13-digit Thai ID
    first_name    TEXT    NOT NULL,
    last_name     TEXT    NOT NULL,
    date_of_birth TEXT,                      -- YYYY-MM-DD
    gender        TEXT    CHECK (gender IN ('M','F','Other')),
    phone         TEXT,
    department    TEXT,                      -- company dept / ward (from Excel import)
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    created_by    INTEGER REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_patients_national_id ON patients(national_id);
CREATE INDEX IF NOT EXISTS idx_patients_hn          ON patients(hn);

-- -------------------------------------------------------------
-- 4. PATIENT_MEDICAL_HISTORY  (1-to-1 with patients, upserted on import)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_medical_history (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id        INTEGER NOT NULL UNIQUE REFERENCES patients(id) ON DELETE CASCADE,

    -- Underlying chronic conditions — stored as comma-separated text
    -- e.g. "HT, DM Type2, DLP, CKD"
    conditions        TEXT,

    -- Allergies (free text, may be structured later)
    drug_allergies    TEXT,
    food_allergies    TEXT,

    -- Current regular medications (free text or comma-separated)
    medications       TEXT,

    -- Smoking / drinking (lifestyle flags)
    is_smoker         INTEGER DEFAULT 0,    -- 0/1
    is_drinker        INTEGER DEFAULT 0,    -- 0/1

    notes             TEXT,
    updated_at        TEXT    DEFAULT (datetime('now','localtime')),
    updated_by        INTEGER REFERENCES users(id)
);

-- -------------------------------------------------------------
-- 5. SESSION_PATIENTS  (enrolment + check-in status per visit)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS session_patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id)  ON DELETE CASCADE,
    patient_id      INTEGER NOT NULL REFERENCES patients(id)  ON DELETE CASCADE,
    queue_no        INTEGER,
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','checked_in','done','absent')),
    checked_in_at   TEXT,
    checked_in_by   INTEGER REFERENCES users(id),
    notes           TEXT,
    UNIQUE (session_id, patient_id)
);

CREATE INDEX IF NOT EXISTS idx_sp_session  ON session_patients(session_id);
CREATE INDEX IF NOT EXISTS idx_sp_patient  ON session_patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_sp_status   ON session_patients(session_id, status);

-- -------------------------------------------------------------
-- 6. VITALS  (one row per patient per session)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vitals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id)  ON DELETE CASCADE,
    patient_id      INTEGER NOT NULL REFERENCES patients(id)  ON DELETE CASCADE,
    weight_kg       REAL,
    height_cm       REAL,
    bmi             REAL,
    waist_cm        REAL,
    systolic_bp     INTEGER,
    diastolic_bp    INTEGER,
    pulse_bpm       INTEGER,
    recorded_at     TEXT    DEFAULT (datetime('now','localtime')),
    updated_at      TEXT    DEFAULT (datetime('now','localtime')),
    recorded_by     INTEGER REFERENCES users(id),
    UNIQUE (session_id, patient_id)
);

-- -------------------------------------------------------------
-- 7. LAB_RESULTS  (one row per patient per session)
--    Historical imports create a session row with is_historical=1
--    and then insert into this same table — the timeline view
--    simply joins across sessions ordered by session_date.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lab_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id)  ON DELETE CASCADE,
    patient_id      INTEGER NOT NULL REFERENCES patients(id)  ON DELETE CASCADE,

    -- Glucose
    fbs             REAL,        -- mg/dL  Fasting Blood Sugar
    hba1c           REAL,        -- %

    -- Lipid Profile
    total_chol      REAL,        -- mg/dL
    hdl             REAL,        -- mg/dL
    ldl             REAL,        -- mg/dL
    triglyceride    REAL,        -- mg/dL

    -- Renal
    creatinine      REAL,        -- mg/dL
    bun             REAL,        -- mg/dL
    uric_acid       REAL,        -- mg/dL
    egfr            REAL,        -- mL/min/1.73 m²

    -- Liver
    sgot_ast        REAL,        -- U/L
    sgpt_alt        REAL,        -- U/L

    -- CBC
    hb              REAL,        -- g/dL   Haemoglobin
    hct             REAL,        -- %      Haematocrit
    wbc             REAL,        -- ×10³/µL
    platelet        REAL,        -- ×10³/µL

    -- Urine Dipstick
    ua_glucose      TEXT,        -- Negative / Trace / 1+ / 2+ / 3+
    ua_protein      TEXT,
    ua_blood        TEXT,

    -- Thyroid (optional)
    tsh             REAL,        -- mIU/L

    recorded_at     TEXT    DEFAULT (datetime('now','localtime')),
    updated_at      TEXT    DEFAULT (datetime('now','localtime')),
    recorded_by     INTEGER REFERENCES users(id),
    UNIQUE (session_id, patient_id)
);

CREATE INDEX IF NOT EXISTS idx_lab_patient  ON lab_results(patient_id);
CREATE INDEX IF NOT EXISTS idx_lab_session  ON lab_results(session_id);

-- -------------------------------------------------------------
-- 8. CUSTOM_LAB_RESULTS  (user-defined extra tests not in the template)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS custom_lab_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id)  ON DELETE CASCADE,
    patient_id  INTEGER NOT NULL REFERENCES patients(id)  ON DELETE CASCADE,
    test_name   TEXT    NOT NULL,
    value       TEXT,
    unit        TEXT,
    recorded_at TEXT    DEFAULT (datetime('now','localtime')),
    recorded_by INTEGER REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_custom_lab ON custom_lab_results(patient_id, session_id);

-- -------------------------------------------------------------
-- 9. VACCINATIONS  (many rows per patient per session)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vaccinations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL REFERENCES sessions(id)  ON DELETE CASCADE,
    patient_id   INTEGER NOT NULL REFERENCES patients(id)  ON DELETE CASCADE,
    vaccine_name TEXT    NOT NULL,
    dose_no      TEXT,                   -- เข็มที่ 1, เข็มที่ 2, Booster
    lot_number   TEXT,
    route        TEXT,                   -- IM / SC / ID / Oral
    site         TEXT,                   -- ต้นแขนซ้าย / ต้นแขนขวา / etc.
    notes        TEXT,
    given_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    given_by     INTEGER REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_vax_patient ON vaccinations(patient_id);
CREATE INDEX IF NOT EXISTS idx_vax_session ON vaccinations(session_id);

-- -------------------------------------------------------------
-- 10. IMPORT_LOG  (audit trail for every Excel/CSV import)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS import_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER NOT NULL REFERENCES sessions(id),
    filename      TEXT    NOT NULL,
    total_rows    INTEGER NOT NULL,
    imported_rows INTEGER NOT NULL,
    updated_rows  INTEGER NOT NULL DEFAULT 0,  -- upserted existing patients
    new_rows      INTEGER NOT NULL DEFAULT 0,  -- brand-new patient records
    skipped_rows  INTEGER NOT NULL DEFAULT 0,
    error_detail  TEXT,                        -- JSON array of per-row errors
    imported_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    imported_by   INTEGER REFERENCES users(id)
);

-- -------------------------------------------------------------
-- 11. EXPORT_LOG  (audit trail for Excel / backup exports)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS export_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER REFERENCES sessions(id),
    export_type   TEXT    NOT NULL,   -- 'excel_daily' | 'full_backup'
    filename      TEXT    NOT NULL,
    exported_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    exported_by   INTEGER REFERENCES users(id)
);

-- -------------------------------------------------------------
-- 12. AUDIT_LOG  (who did what and when)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER REFERENCES users(id),
    user_name    TEXT    NOT NULL,
    action       TEXT    NOT NULL,
    detail       TEXT,
    performed_at TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_audit_performed ON audit_log(performed_at);

-- -------------------------------------------------------------
-- Default admin user (password replaced at runtime by connection.py)
-- -------------------------------------------------------------
INSERT OR IGNORE INTO users (username, password_hash, full_name, role)
VALUES ('admin', 'placeholder', 'Administrator', 'admin');
