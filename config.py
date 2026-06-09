import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle:
    #   sys.executable  → path to the .exe
    #   sys._MEIPASS    → temp folder where bundled read-only assets are unpacked
    _EXE_DIR = Path(sys.executable).parent   # persistent data lives here
    _ASSETS  = Path(sys._MEIPASS)            # bundled read-only files live here
else:
    _EXE_DIR = Path(__file__).parent
    _ASSETS  = _EXE_DIR

BASE_DIR    = _EXE_DIR
DB_PATH     = BASE_DIR / "database" / "clinic.db"
SCHEMA_PATH = _ASSETS  / "database" / "schema.sql"
EXPORTS_DIR = BASE_DIR / "exports"
BACKUPS_DIR = BASE_DIR / "backups"
ASSETS_DIR  = _ASSETS  / "assets"

APP_TITLE   = "BPK1 MOBILE UNIT — Health Screening System"
APP_VERSION = "1.0.0"

HN_PREFIX      = "HN"   # HN-YYMM-XXXX
SESSION_PREFIX = "SS"   # SS-YYYY-NNN

THEME_COLOR = "#1a6bb5"   # primary blue

LOGO_PATH = str(ASSETS_DIR / "logo.png")

# ── Hospital identity (แก้ที่นี่ที่เดียว) ─────────────────────────────────────
HOSP_NAME_TH  = "โรงพยาบาลบางปะกอก 1"
HOSP_NAME_EN  = "BANGPAKOK 1 HOSPITAL"
HOSP_NAME_SHORT = "บางปะกอก 1"
HOSP_PHONE    = "02-109-1111"
HOSP_ADDRESS  = "9 ถนนนราธิวาสราชนครินทร์ แขวงช่องนนทรี เขตยานนาวา กรุงเทพฯ 10120"
