from datetime import datetime
from database.connection import get_connection


def generate_hn() -> str:
    """
    Returns next available HN in format  HN-YYMM-XXXX.
    Sequence resets each calendar month.
    Example: HN-2601-0001 (Jan 2026, patient #1)
    """
    prefix = datetime.now().strftime("%y%m")   # "2601" for Jan 2026
    conn = get_connection()

    row = conn.execute(
        "SELECT hn FROM patients WHERE hn LIKE ? ORDER BY hn DESC LIMIT 1",
        (f"HN-{prefix}-%",),
    ).fetchone()

    seq = int(row["hn"].rsplit("-", 1)[-1]) + 1 if row else 1
    return f"HN-{prefix}-{seq:04d}"
