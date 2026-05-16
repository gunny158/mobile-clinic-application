"""Thai Buddhist Era date helpers. BE = CE + 543."""
from __future__ import annotations
from datetime import date, datetime

_MONTHS_TH = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


def be(year_ce: int) -> int:
    return year_ce + 543


def fmt_date_be(dob_str) -> str:
    """'DD/MM/YYYY(BE)' from ISO date string."""
    try:
        d = date.fromisoformat(str(dob_str)[:10])
        return f"{d.day:02d}/{d.month:02d}/{be(d.year)}"
    except Exception:
        return str(dob_str)[:10] if dob_str else "—"


def fmt_datetime_be(dt_str) -> str:
    """'DD/MM/YYYY(BE) HH:MM' from ISO datetime string."""
    try:
        dt = datetime.fromisoformat(str(dt_str)[:19])
        return f"{dt.day:02d}/{dt.month:02d}/{be(dt.year)}  {dt.hour:02d}:{dt.minute:02d}"
    except Exception:
        return str(dt_str)[:16] if dt_str else "—"


def fmt_time(dt_str) -> str:
    """'HH:MM' only — no year conversion needed."""
    try:
        return datetime.fromisoformat(str(dt_str)[:19]).strftime("%H:%M")
    except Exception:
        return str(dt_str)[:5] if dt_str else "—"


def today_be_long() -> str:
    """Today as 'D MonthTH YYYY(BE)'."""
    t = date.today()
    return f"{t.day} {_MONTHS_TH[t.month]} {be(t.year)}"
