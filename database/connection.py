import sqlite3
import bcrypt
from config import DB_PATH, SCHEMA_PATH

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_schema()
    return _conn


def _init_schema() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    _conn.executescript(sql)          # commits automatically, creates all tables
    _conn.commit()
    _migrate()
    _seed_admin_password()


def _migrate() -> None:
    """Add columns that were added after initial schema creation."""
    _safe_add_column("vitals",      "bmi",        "REAL")
    _safe_add_column("vitals",      "updated_at", "TEXT")
    _safe_add_column("lab_results", "updated_at", "TEXT")


def _safe_add_column(table: str, column: str, col_type: str) -> None:
    try:
        _conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        _conn.commit()
    except Exception:
        pass   # column already exists


def _seed_admin_password() -> None:
    """Replace the placeholder hash on first run."""
    row = _conn.execute(
        "SELECT password_hash FROM users WHERE username = 'admin'"
    ).fetchone()
    if row and "placeholder" in row["password_hash"]:
        hashed = bcrypt.hashpw(b"admin1234", bcrypt.gensalt()).decode()
        _conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (hashed,),
        )
        _conn.commit()
