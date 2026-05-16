import re
from datetime import datetime


def validate_national_id(nid: str) -> bool:
    """Thai 13-digit national ID with checksum verification."""
    nid = nid.strip().replace("-", "").replace(" ", "")
    if not re.fullmatch(r"\d{13}", nid):
        return False
    digits = [int(c) for c in nid]
    total = sum(d * (13 - i) for i, d in enumerate(digits[:12]))
    check = (11 - (total % 11)) % 10
    return check == digits[12]


def validate_date(date_str: str) -> bool:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            datetime.strptime(date_str.strip(), fmt)
            return True
        except ValueError:
            pass
    return False


def normalise_date(date_str: str) -> str | None:
    """Return ISO-8601 (YYYY-MM-DD, CE) or None if unparseable.
    BE years (>= 2500) are converted to CE automatically."""
    s = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            yr = dt.year - 543 if dt.year >= 2500 else dt.year
            return f"{yr:04d}-{dt.month:02d}-{dt.day:02d}"
        except ValueError:
            pass
    return None


def validate_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"0\d{8,9}", phone.strip().replace("-", "")))
