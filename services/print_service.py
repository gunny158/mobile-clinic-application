"""Generate A5 vaccine consent form PDF for printing."""
from __future__ import annotations
import io
import os
import tempfile
from datetime import date

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from config import HOSP_NAME_TH, HOSP_NAME_EN, HOSP_NAME_SHORT, HOSP_PHONE

_REGISTERED: set[str] = set()

_FONT_CANDIDATES = [
    ("AngsanaUPC",     r"C:\Windows\Fonts\angsau.ttf"),
    ("AngsanaNew",     r"C:\Windows\Fonts\angsa.ttf"),
    ("Tahoma",         r"C:\Windows\Fonts\tahoma.ttf"),
]
_FONT_BOLD_CANDIDATES = [
    ("AngsanaUPCBold", r"C:\Windows\Fonts\angsaub.ttf"),
    ("AngsanaNewBold", r"C:\Windows\Fonts\angsab.ttf"),
    ("TahomaBold",     r"C:\Windows\Fonts\tahomabd.ttf"),
]


def _register_fonts() -> tuple[str, str]:
    """Register Thai-capable fonts, return (regular, bold) font names."""
    reg = "Helvetica"
    bold = "Helvetica-Bold"

    for name, path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                if name not in _REGISTERED:
                    pdfmetrics.registerFont(TTFont(name, path))
                    _REGISTERED.add(name)
                reg = name
                break
            except Exception:
                continue

    for name, path in _FONT_BOLD_CANDIDATES:
        if os.path.exists(path):
            try:
                if name not in _REGISTERED:
                    pdfmetrics.registerFont(TTFont(name, path))
                    _REGISTERED.add(name)
                bold = name
                break
            except Exception:
                continue

    return reg, bold


def _make_barcode_reader(hn: str) -> ImageReader | None:
    """Generate Code128 barcode and return a ReportLab ImageReader."""
    try:
        import barcode as _bc
        from barcode.writer import ImageWriter

        writer = ImageWriter()
        writer.set_options({
            "module_width":  0.5,
            "module_height": 8.0,
            "font_size":     7,
            "text_distance": 2,
            "quiet_zone":    2.0,
            "dpi":           150,
        })
        bc_cls = _bc.get_barcode_class("code128")
        bc_obj = bc_cls(hn.replace("-", ""), writer=writer)
        buf = io.BytesIO()
        bc_obj.write(buf)
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        return None


def generate_vaccine_consent(
    patient: dict,
    session_date: str,
    logo_path: str | None = None,
) -> str:
    """
    Generate A5 vaccine consent form PDF.

    Args:
        patient:      dict with at least first_name, last_name, hn
        session_date: display string e.g. "09/06/2568"
        logo_path:    path to PNG/JPG logo file (optional)

    Returns:
        Path to the generated temp PDF file.
    """
    font, font_bold = _register_fonts()

    fd, out_path = tempfile.mkstemp(suffix=".pdf", prefix="vaccine_consent_")
    os.close(fd)

    W, H = A5   # 419.5 x 595.3 pts  (148 mm × 210 mm)
    c = canvas.Canvas(out_path, pagesize=A5)

    hn   = patient.get("hn", "")
    name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()

    # ─── Header (top 30 mm) ────────────────────────────────────────────────
    HDR_H = 30 * mm
    hdr_y = H - HDR_H   # y-coordinate of bottom of header zone

    # Logo (top-left)
    has_logo = logo_path and os.path.exists(logo_path)
    if has_logo:
        c.drawImage(
            logo_path,
            x=8 * mm, y=hdr_y + 3 * mm,
            width=28 * mm, height=24 * mm,
            preserveAspectRatio=True, mask="auto",
        )
        hosp_x = 40 * mm
    else:
        hosp_x = 8 * mm

    # Hospital name block
    c.setFont(font_bold, 15)
    c.setFillColor(colors.HexColor("#003366"))
    c.drawString(hosp_x, H - 12 * mm, HOSP_NAME_SHORT)
    c.setFont(font, 10)
    c.drawString(hosp_x, H - 18 * mm, HOSP_NAME_EN)
    c.setFont(font, 9)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(hosp_x, H - 23 * mm, f"โทร. {HOSP_PHONE}")

    # Barcode (top-right)
    bc_reader = _make_barcode_reader(hn)
    if bc_reader:
        c.drawImage(
            bc_reader,
            x=W - 48 * mm, y=hdr_y + 3 * mm,
            width=40 * mm, height=22 * mm,
            preserveAspectRatio=True,
        )
    else:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawRightString(W - 8 * mm, H - 14 * mm, f"HN: {hn}")

    # Divider line
    c.setStrokeColor(colors.HexColor("#003366"))
    c.setLineWidth(1.5)
    c.line(8 * mm, hdr_y, W - 8 * mm, hdr_y)

    # ── Layout constants ───────────────────────────────────────────────────
    BOX   = 3.5 * mm   # checkbox size
    LEFT  = 8 * mm     # left margin
    BODY  = 10 * mm    # bullet indent

    # ─── Form title ────────────────────────────────────────────────────────
    y = hdr_y - 8 * mm
    c.setFont(font_bold, 13)
    c.setFillColor(colors.black)
    c.drawCentredString(W / 2, y, "แบบสอบถามผู้มารับบริการ")

    # ─── Vaccine type selector ─────────────────────────────────────────────
    y -= 7 * mm
    c.setFont(font_bold, 11)
    c.drawString(LEFT, y, "วัคซีนป้องกันโรคไข้หวัดใหญ่")

    # "□ 3 สายพันธุ์" checkbox
    lbl_x = LEFT + 57 * mm
    c.rect(lbl_x, y - 1 * mm, BOX, BOX, stroke=1, fill=0)
    c.setFont(font, 11)
    c.drawString(lbl_x + 4.5 * mm, y, "3 สายพันธุ์")

    # "□ 4 สายพันธุ์" checkbox
    lbl_x2 = lbl_x + 22 * mm
    c.rect(lbl_x2, y - 1 * mm, BOX, BOX, stroke=1, fill=0)
    c.drawString(lbl_x2 + 4.5 * mm, y, "4 สายพันธุ์  ตามฤดูกาล")

    # ─── Patient info ──────────────────────────────────────────────────────
    y -= 8 * mm
    c.setFont(font, 11)
    c.drawString(LEFT, y, f"ชื่อ – สกุล:  {name}")
    c.drawString(W / 2, y, f"วันที่:  {session_date}")

    y -= 7 * mm
    c.drawString(LEFT, y,
        "โรคประจำตัว: ...........................................................................")

    y -= 7 * mm
    c.drawString(LEFT, y,
        "ตรวจวัดอุณหภูมิได้: ...........................................................................")

    # ─── Checklist instruction ─────────────────────────────────────────────
    y -= 8 * mm
    c.setFont(font, 10)
    c.setFillColor(colors.HexColor("#444444"))
    c.drawString(LEFT, y,
        "สำหรับคำถามต่อไปนี้จะช่วยพิจารณาวัคซีนที่คุณจะได้รับในวันนี้  "
        "กรุณาทำเครื่องหมาย (  ) ในช่อง")

    # ─── Checklist table ───────────────────────────────────────────────────
    # (line1, line2_or_None) — line2 wraps long items to a second line
    items = [
        ("เคยได้รับการฉีดวัคซีนไข้หวัดใหญ่",                              None),
        ("มีประวัติแพ้ไข่ไก่อย่างรุนแรง",                                  None),
        ("เคยแพ้วัคซีนไข้หวัดใหญ่ หรือ",
         "   แพ้สารประกอบอื่นในวัคซีนอย่างรุนแรง **"),
        ("กำลังมีไข้",                                                       None),
        ("ยังมีโรคประจำตัวที่อาการกำเริบ เช่น ใจสั่น เจ็บแน่นหน้าอก",
         "   หอบเหนื่อย หรือยังควบคุมอาการของโรคไม่ได้"),
        ("ตั้งครรภ์ มีอายุครรภ์น้อยกว่า 18 สัปดาห์",                      None),
    ]

    ROW_S  = 7.5 * mm  # single-line row height
    L2_GAP = 5.0 * mm  # drop from line1 to line2
    L2_BOT = 6.0 * mm  # drop from line2 to next item

    y -= 7 * mm        # gap between instruction and first checklist item
    c.setFont(font, 10)
    c.setFillColor(colors.black)

    for line1, line2 in items:
        c.drawString(BODY, y, f"•  {line1}")
        c.rect(W - 34 * mm, y - 1 * mm, BOX, BOX, stroke=1, fill=0)
        c.setFont(font, 9)
        c.drawString(W - 29 * mm, y, "ใช่")
        c.rect(W - 19 * mm, y - 1 * mm, BOX, BOX, stroke=1, fill=0)
        c.drawString(W - 14 * mm, y, "ไม่ใช่")
        c.setFont(font, 10)

        if line2:
            y -= L2_GAP
            c.drawString(14 * mm, y, line2)
            y -= L2_BOT
        else:
            y -= ROW_S

    # ─── Consent acknowledgment ────────────────────────────────────────────
    y -= 3 * mm
    c.setFont(font, 10)
    c.rect(LEFT, y - 1 * mm, BOX, BOX, stroke=1, fill=0)
    c.drawString(LEFT + 6 * mm, y,
        "ท่านได้รับข้อมูลเกี่ยวกับวัคซีนไข้หวัดใหญ่และได้ทำความเข้าใจแล้ว")

    # ─── Patient signature ─────────────────────────────────────────────────
    y -= 13 * mm
    c.setFont(font, 10)
    c.drawString(LEFT, y, "ลงชื่อ .............................................................................")
    y -= 7 * mm
    c.setFont(font, 9)
    c.drawString(LEFT, y, f"(  {name}  )  ผู้รับบริการ")

    # ─── Allergy warning (after patient sig, before nurse) ────────────────
    y -= 10 * mm
    c.setFont(font, 10)
    c.setFillColor(colors.black)
    c.drawString(LEFT, y,
        "** อาการแพ้อย่างรุนแรง เช่น หายใจไม่สะดวก เสียงแหบ ลมพิษ ซีดขาว อ่อนเพลีย")
    y -= 6 * mm
    c.drawString(LEFT, y, "   หัวใจเต้นเร็ว หรือเวียนศีรษะ")

    # ─── Nurse signature (last) ────────────────────────────────────────────
    y -= 12 * mm
    c.setFont(font, 10)
    c.drawString(LEFT, y, "พยาบาลผู้ฉีด .........................................................................")
    y -= 7 * mm
    c.setFont(font, 9)
    c.drawString(LEFT, y, "(  .................................................  )")

    c.save()
    return out_path


def print_consent_form(patient: dict, session_date: str, logo_path: str | None = None) -> None:
    """Generate PDF and open with the default PDF viewer (triggers print dialog)."""
    pdf_path = generate_vaccine_consent(patient, session_date, logo_path)
    try:
        os.startfile(pdf_path, "print")
    except Exception:
        os.startfile(pdf_path)
