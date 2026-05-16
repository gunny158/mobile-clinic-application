"""
Barcode generation and thermal label printing.

Label layout (default 40 mm × 20 mm, scalable):
  Line 1:  name  (bold)
  Line 2:  HN | Gender | Reg.date  (info line)
  Line 3:  Barcode (Code128)
  Line 4:  HN digits below barcode bars
"""
from __future__ import annotations
import io
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── sticker sizes ──────────────────────────────────────────────────────────────
# Each entry: display_name → (width_mm, height_mm)
STICKER_SIZES: dict[str, tuple[float, float]] = {
    "4×2 cm  (มาตรฐาน)": (40.0, 20.0),
    "5×3 cm":              (50.0, 30.0),
    "5.8×4 cm  (ใหญ่)":   (58.0, 40.0),
}
DEFAULT_SIZE = "4×2 cm  (มาตรฐาน)"

DPI = 203  # typical thermal printer resolution

_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    key = (name, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(name, size)
        except OSError:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def _win_font(ttf_name: str, size: int) -> ImageFont.FreeTypeFont:
    """Try Windows Fonts folder first, then fall back to default."""
    paths = [
        Path("C:/Windows/Fonts") / ttf_name,
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / ttf_name,
    ]
    for p in paths:
        if p.exists():
            return _font(str(p), size)
    return ImageFont.load_default()


def _layout(w_mm: float, h_mm: float) -> dict:
    """Pixel dims and font sizes scaled proportionally from the 58 mm baseline."""
    scale = w_mm / 58.0
    return {
        "w_px":     int(w_mm / 25.4 * DPI),
        "h_px":     int(h_mm / 25.4 * DPI),
        "margin":   max(6,  int(10 * scale)),
        "f_name":   max(16, int(26 * scale)),
        "f_info":   max(13, int(18 * scale)),
        "f_small":  max(11, int(13 * scale)),
        "bc_h":     max(38, int(65 * scale)),
        "name_max": max(18, int(30 * scale)),
    }


# ── barcode image (Code128) ─────────────────────────────────────────────────

def _barcode_image(data: str, width_px: int, height_px: int) -> Image.Image:
    """Return a PIL Image of a Code128 barcode (no text below)."""
    try:
        import barcode as _bc
        from barcode.writer import ImageWriter

        writer = ImageWriter()
        writer.set_options({
            "module_width":  0.4,
            "module_height": 8.0,
            "font_size":     0,
            "text_distance": 0,
            "quiet_zone":    1.5,
            "dpi":           DPI,
        })
        bc_cls = _bc.get_barcode_class("code128")
        bc_obj = bc_cls(data, writer=writer)

        buf = io.BytesIO()
        bc_obj.write(buf)
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
        return img.resize((width_px, height_px), Image.LANCZOS)
    except Exception:
        # Fallback: plain white image
        img = Image.new("RGB", (width_px, height_px), "white")
        ImageDraw.Draw(img).text((4, 4), f"[{data}]", fill="black")
        return img


# ── public: generate label PNG ──────────────────────────────────────────────

def generate_label(
    hn: str,
    full_name: str,
    gender: str | None = None,
    date_of_birth: str | None = None,
    queue_no: int | None = None,
    barcode_data: str | None = None,
    label_w_mm: float = 40.0,
    label_h_mm: float = 20.0,
) -> Image.Image:
    """
    Label layout (top → bottom):
      1. Name  (bold)
      2. HN  |  Gender  |  DOB (BE)  (info line)
      3. Barcode  (Code128)
      4. HN digits below barcode bars

    Font sizes and barcode height scale proportionally with label_w_mm.
    """
    lp      = _layout(label_w_mm, label_h_mm)
    bc_data = barcode_data or hn.replace("-", "")

    img  = Image.new("RGB", (lp["w_px"], lp["h_px"]), "white")
    draw = ImageDraw.Draw(img)

    f_name  = _win_font("tahomabd.ttf", lp["f_name"])
    f_info  = _win_font("cour.ttf",     lp["f_info"])
    f_small = _win_font("tahoma.ttf",   lp["f_small"])

    MARGIN = lp["margin"]
    W      = lp["w_px"]
    y      = MARGIN

    def _draw_centered(text: str, font, color: str = "black") -> None:
        nonlocal y
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((max(MARGIN, (W - tw) // 2), y), text, font=font, fill=color)
        y += th + 4

    # ── 1. Name ────────────────────────────────────────────────────────────
    _draw_centered(full_name[:lp["name_max"]], f_name)

    # Thin divider
    draw.line([(MARGIN, y), (W - MARGIN, y)], fill="#bbbbbb", width=1)
    y += 4

    # ── 2. Info line:  HN  │  M/F  │  DOB (BE) ───────────────────────────
    gender_str = (gender or "").upper()
    if gender_str not in ("M", "F"):
        gender_str = ""

    date_str = ""
    if date_of_birth:
        try:
            from datetime import date as _date
            d = _date.fromisoformat(str(date_of_birth)[:10])
            date_str = f"{d.day:02d}/{d.month:02d}/{d.year + 543}"
        except Exception:
            date_str = str(date_of_birth)[:10]

    parts = [hn]
    if gender_str:
        parts.append(gender_str)
    if date_str:
        parts.append(date_str)
    info_line = "  |  ".join(parts)

    _draw_centered(info_line, f_info)
    y += 2

    # ── 3. Barcode ─────────────────────────────────────────────────────────
    bc_h   = lp["bc_h"]
    bc_img = _barcode_image(bc_data, W - MARGIN * 2, bc_h)
    img.paste(bc_img, (MARGIN, y))
    y += bc_h + 2

    # ── 4. Digits below bars ───────────────────────────────────────────────
    _draw_centered(bc_data, f_small, color="#555555")

    return img


# ── public: save to temp PNG ────────────────────────────────────────────────

def save_label_png(img: Image.Image) -> str:
    """Save label image to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".png", prefix="label_")
    os.close(fd)
    img.save(path, dpi=(DPI, DPI))
    return path


# ── public: print ───────────────────────────────────────────────────────────

def print_label(
    hn: str,
    full_name: str,
    gender: str | None = None,
    date_of_birth: str | None = None,
    queue_no: int | None = None,
    label_w_mm: float = 40.0,
    label_h_mm: float = 20.0,
) -> None:
    """Send a single label to the default Windows printer (os.startfile fallback)."""
    img  = generate_label(hn, full_name, gender, date_of_birth, queue_no,
                          label_w_mm=label_w_mm, label_h_mm=label_h_mm)
    path = save_label_png(img)

    try:
        import win32print, win32ui
        from PIL import ImageWin

        printer_name = win32print.GetDefaultPrinter()
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        hdc.StartDoc(f"Label_{hn}")
        hdc.StartPage()

        pw = hdc.GetDeviceCaps(8)    # HORZRES
        ph = hdc.GetDeviceCaps(10)   # VERTRES
        dib = ImageWin.Dib(img)
        dib.draw(hdc.GetHandleAttrib(), (0, 0, pw, ph))

        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
    except Exception:
        os.startfile(path)           # fallback: open with default viewer / print dialog


# ── public: batch PDF ───────────────────────────────────────────────────────

def generate_batch_pdf(
    patients: list[dict],
    label_w_mm: float = 40.0,
    label_h_mm: float = 20.0,
) -> str:
    """
    Build a PDF with one label per page for each patient dict.
    patients: list of dicts with keys: hn, first_name, last_name, queue_no (optional)
    Returns path to the temp PDF file.
    """
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas

    page_w = label_w_mm * mm
    page_h = label_h_mm * mm

    fd, pdf_path = tempfile.mkstemp(suffix=".pdf", prefix="stickers_")
    os.close(fd)

    c = rl_canvas.Canvas(pdf_path, pagesize=(page_w, page_h))
    for p in patients:
        full_name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        img = generate_label(
            p["hn"], full_name,
            gender=p.get("gender"),
            date_of_birth=p.get("date_of_birth"),
            queue_no=p.get("queue_no"),
            label_w_mm=label_w_mm,
            label_h_mm=label_h_mm,
        )
        png_path = save_label_png(img)

        c.setPageSize((page_w, page_h))
        c.drawImage(png_path, 0, 0, width=page_w, height=page_h)
        c.showPage()

    c.save()
    return pdf_path
