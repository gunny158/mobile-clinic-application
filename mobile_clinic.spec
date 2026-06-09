# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for BPK1 Mobile Clinic.
# Build command:  python -m PyInstaller mobile_clinic.spec --clean --noconfirm
# Output:         dist/BPK1_MobileClinic/
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ── Bundled data files (read-only assets) ────────────────────────────────────
datas = [
    # App schema — must be inside the bundle so it can be read on first run
    ("database/schema.sql", "database"),
    # Logo and assets folder
    ("assets/logo.png", "assets"),
]
datas += collect_data_files("customtkinter")   # themes, images, fonts
datas += collect_data_files("barcode")         # barcode writer SVG templates
datas += collect_data_files("reportlab")       # fonts, color profiles

# ── Hidden imports (dynamic/lazy loaders that PyInstaller misses) ─────────────
hiddenimports = [
    # customtkinter
    "customtkinter",
    # PIL
    "PIL", "PIL.Image", "PIL.ImageTk", "PIL.ImageDraw", "PIL.ImageFont",
    # data / office
    "pandas", "pandas.core.arrays.arrow",
    "openpyxl", "openpyxl.styles", "openpyxl.utils", "openpyxl.cell",
    "openpyxl.reader.excel",
    # barcode
    "barcode", "barcode.codex", "barcode.writer",
    # PDF
    "reportlab", "reportlab.pdfgen", "reportlab.pdfgen.canvas",
    "reportlab.lib", "reportlab.lib.pagesizes", "reportlab.lib.units",
    "reportlab.platypus",
    # Windows printing
    "win32api", "win32con", "win32print",
    # auth
    "bcrypt",
    # stdlib (usually auto-detected but safe to declare)
    "sqlite3", "threading", "pathlib", "logging",
]
hiddenimports += collect_submodules("openpyxl")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest", "pydoc", "doctest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BPK1_MobileClinic",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX can trigger antivirus; leave off for clinic PCs
    console=False,      # no console window
    icon=None,          # replace with "assets/icon.ico" if you add one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="BPK1_MobileClinic",
)
