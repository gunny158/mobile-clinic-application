"""Excel / CSV import wizard — two-step: file select → preview → confirm."""
from __future__ import annotations
from typing import Callable
import threading
import tkinter.filedialog as fd
import customtkinter as ctk

from services.import_service import ImportService, ImportPreview, ImportResult

_STATUS_COLOR = {"ok": "#2e7d32", "error": "#c62828"}
_STATUS_ICON  = {"ok": "✅", "error": "❌"}


class ImportDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        user_id: int,
        session_id: int | None,
        on_complete: Callable[[ImportResult], None],
    ) -> None:
        super().__init__(parent)
        self._svc        = ImportService()
        self._user_id    = user_id
        self._session_id = session_id
        self._on_complete = on_complete
        self._preview: ImportPreview | None = None

        self.title("📥  Import ผู้ป่วยจาก Excel / CSV")
        self.resizable(False, False)
        self.grab_set()
        self._center(700, 560)

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        self._show_step1()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _clear(self) -> None:
        for w in self._content.winfo_children():
            w.destroy()

    # ── Step 1: file selection ─────────────────────────────────────────

    def _show_step1(self) -> None:
        self._clear()
        f = self._content

        ctk.CTkLabel(
            f, text="📥  เลือกไฟล์ Excel หรือ CSV",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
        ).pack(pady=(24, 4))
        ctk.CTkLabel(
            f, text="ระบบรองรับไฟล์ .xlsx  .xls  .csv",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="gray",
        ).pack()

        # Template reference card
        ref = ctk.CTkFrame(f, fg_color="#f0f4f8", corner_radius=10)
        ref.pack(fill="x", padx=32, pady=20)

        ctk.CTkLabel(
            ref, text="คอลัมน์ที่รองรับ",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 4))

        cols_text = (
            "Demographics:  national_id · hn · first_name · last_name · dob · gender · phone · department\n"
            "ประวัติสุขภาพ:  conditions · drug_allergies · food_allergies · medications · is_smoker · is_drinker\n"
            "ผลแล็บย้อนหลัง (ปี พ.ศ.):  fbs_2566 · hba1c_2566 · ldl_2567 · creatinine_2567 · …\n"
            "                 หรือ (ปี ค.ศ.):  fbs_2023 · hba1c_2023 · ldl_2024 · … (รับทั้งสองแบบ)"
        )
        ctk.CTkLabel(
            ref, text=cols_text,
            font=ctk.CTkFont(family="Courier New", size=14, weight="bold"),
            text_color="#37474f", justify="left", anchor="w", wraplength=620,
        ).pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            ref,
            text="ℹ  national_id เป็นตัวเลือก — ระบบค้นหาซ้ำด้วย: national_id → hn → ชื่อ+นามสกุล (+วันเกิด)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#1565c0", anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 12))

        self._lbl_filepath = ctk.CTkLabel(
            f, text="ยังไม่ได้เลือกไฟล์",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="gray",
        )
        self._lbl_filepath.pack(pady=4)

        self._lbl_err1 = ctk.CTkLabel(
            f, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e53935",
        )
        self._lbl_err1.pack()

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(pady=16)

        ctk.CTkButton(
            btn_row, text="📂  เลือกไฟล์",
            width=160, height=42,
            fg_color="#455a64", hover_color="#37474f",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._pick_file,
        ).pack(side="left", padx=8)

        self._btn_next = ctk.CTkButton(
            btn_row, text="ถัดไป  ▶",
            width=140, height=42,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            state="disabled",
            command=self._parse_and_preview,
        )
        self._btn_next.pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row, text="ยกเลิก",
            width=100, height=42,
            fg_color="#e0e0e0", hover_color="#bdbdbd",
            text_color="#212121",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _pick_file(self) -> None:
        path = fd.askopenfilename(
            title="เลือกไฟล์ Excel หรือ CSV",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files",   "*.csv"),
                ("All files",   "*.*"),
            ],
        )
        if path:
            self._filepath = path
            short = path if len(path) < 60 else "…" + path[-57:]
            self._lbl_filepath.configure(text=f"📄  {short}", text_color="#1a6bb5")
            self._btn_next.configure(state="normal")

    # ── Step 1 → 2: parse file ─────────────────────────────────────────

    def _parse_and_preview(self) -> None:
        self._btn_next.configure(state="disabled", text="กำลังอ่านไฟล์…")
        self._lbl_err1.configure(text="")

        def _work():
            preview = self._svc.parse_file(self._filepath)
            self.after(0, lambda: self._show_step2(preview))

        threading.Thread(target=_work, daemon=True).start()

    # ── Step 2: preview ────────────────────────────────────────────────

    def _show_step2(self, preview: ImportPreview) -> None:
        self._preview = preview
        self._clear()
        f = self._content

        ctk.CTkLabel(
            f, text="🔍  ตรวจสอบข้อมูลก่อน Import",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
        ).pack(pady=(18, 6))

        # Summary bar
        summary = ctk.CTkFrame(f, fg_color="#f0f4f8", corner_radius=10)
        summary.pack(fill="x", padx=24, pady=(0, 10))

        def _chip(label, value, color):
            chip = ctk.CTkFrame(summary, fg_color=color, corner_radius=8)
            chip.pack(side="left", padx=8, pady=10, ipadx=10, ipady=4)
            ctk.CTkLabel(
                chip, text=f"{label}\n{value}",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="white", justify="center",
            ).pack()

        _chip("ทั้งหมด",  preview.total,        "#455a64")
        _chip("ถูกต้อง",  preview.valid,         "#2e7d32")
        _chip("ผู้ป่วยใหม่", preview.new_count,  "#1565c0")
        _chip("อัปเดต",   preview.update_count,  "#f57c00")
        _chip("มีปัญหา",  preview.invalid,       "#c62828")

        if self._session_id:
            ctk.CTkLabel(
                f,
                text="✅  ผู้ป่วยที่นำเข้าสำเร็จจะถูกลงทะเบียนใน Session ปัจจุบันโดยอัตโนมัติ",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#2e7d32",
            ).pack()

        # Row preview table
        hdr = ctk.CTkFrame(f, fg_color="#eef2f7", corner_radius=0, height=32)
        hdr.pack(fill="x", padx=24)
        hdr.pack_propagate(False)
        for text, width in [("แถว", 50), ("ชื่อ-นามสกุล", 200), ("HN/บัตร", 160), ("สถานะ", 220)]:
            ctk.CTkLabel(
                hdr, text=text, width=width, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#37474f",
            ).pack(side="left", padx=(10, 0))

        body = ctk.CTkScrollableFrame(f, fg_color="white", corner_radius=0, height=280)
        body.pack(fill="x", padx=24)

        for i, rp in enumerate(preview.rows[:200]):     # cap display at 200
            bg  = "white" if i % 2 == 0 else "#f7f9fc"
            row = ctk.CTkFrame(body, fg_color=bg, corner_radius=0, height=34)
            row.pack(fill="x")
            row.pack_propagate(False)

            ctk.CTkLabel(
                row, text=str(rp.row_num), width=50,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#546e7a", anchor="w",
            ).pack(side="left", padx=(10, 0))

            ctk.CTkLabel(
                row, text=rp.full_name or "—", width=200,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#212121", anchor="w",
            ).pack(side="left", padx=(8, 0))

            key = rp.hn or rp.national_id or "—"
            ctk.CTkLabel(
                row, text=key, width=160,
                font=ctk.CTkFont(family="Courier New", size=13, weight="bold"),
                text_color="#1a6bb5", anchor="w",
            ).pack(side="left", padx=(8, 0))

            if rp.status == "ok":
                badge_text  = ("🆕 ผู้ป่วยใหม่" if rp.is_new else "🔄 อัปเดต")
                badge_color = "#1565c0" if rp.is_new else "#f57c00"
            else:
                badge_text  = f"❌ {rp.message}"
                badge_color = "#c62828"

            ctk.CTkLabel(
                row, text=badge_text,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=badge_color, anchor="w",
            ).pack(side="left", padx=(8, 0))

            ctk.CTkFrame(body, height=1, fg_color="#f0f0f0").pack(fill="x")

        if len(preview.rows) > 200:
            ctk.CTkLabel(
                body,
                text=f"… และอีก {len(preview.rows) - 200} รายการ",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="gray",
            ).pack(pady=6)

        # Buttons
        self._lbl_err2 = ctk.CTkLabel(
            f, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e53935",
        )
        self._lbl_err2.pack(pady=(6, 0))

        btn_row = ctk.CTkFrame(f, fg_color="transparent")
        btn_row.pack(pady=10)

        ctk.CTkButton(
            btn_row, text="◀  ย้อนกลับ",
            width=120, height=40,
            fg_color="#78909c", hover_color="#607d8b",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._show_step1,
        ).pack(side="left", padx=8)

        confirm_state = "normal" if preview.valid > 0 else "disabled"
        ctk.CTkButton(
            btn_row,
            text=f"✅  ยืนยัน Import  ({preview.valid} รายการ)",
            width=220, height=40,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            state=confirm_state,
            command=self._confirm_import,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row, text="ยกเลิก",
            width=100, height=40,
            fg_color="#e0e0e0", hover_color="#bdbdbd",
            text_color="#212121",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self.destroy,
        ).pack(side="left", padx=8)

    # ── Confirm import ─────────────────────────────────────────────────

    def _confirm_import(self) -> None:
        def _work():
            result = self._svc.execute_import(
                self._preview, self._session_id, self._user_id
            )
            self.after(0, lambda: self._show_result(result))

        threading.Thread(target=_work, daemon=True).start()

    def _show_result(self, result: ImportResult) -> None:
        self._clear()
        f = self._content

        success = result.errors == 0
        icon  = "🎉" if success else "⚠️"
        title = "Import สำเร็จ" if success else "Import เสร็จสิ้น (มีบางรายการผิดพลาด)"
        ctk.CTkLabel(
            f, text=f"{icon}  {title}",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#2e7d32" if success else "#f57c00",
        ).pack(pady=(30, 16))

        info = (
            f"ผู้ป่วยใหม่:    {result.new_patients} ราย\n"
            f"อัปเดต:        {result.updated_patients} ราย\n"
            f"ผิดพลาด:      {result.errors} ราย"
        )
        ctk.CTkLabel(
            f, text=info,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            justify="left",
        ).pack(pady=4)

        if result.error_details:
            err_box = ctk.CTkScrollableFrame(
                f, fg_color="#fff3e0", corner_radius=8, height=120
            )
            err_box.pack(fill="x", padx=32, pady=12)
            for detail in result.error_details:
                ctk.CTkLabel(
                    err_box, text=detail, anchor="w",
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color="#bf360c", wraplength=600,
                ).pack(fill="x", padx=8, pady=1)

        ctk.CTkButton(
            f, text="ปิด",
            width=120, height=40,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=lambda: (self._on_complete(result), self.destroy()),
        ).pack(pady=20)
