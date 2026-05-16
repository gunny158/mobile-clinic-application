"""Sticker / Barcode printing page.

Features:
  • Search patients by name / HN / national_id
  • Filter by session (shows queue_no if enrolled)
  • Checkbox multi-select  ➜  batch print to PDF
  • Single-patient print button on each row
  • Live label preview panel on the right
"""
from __future__ import annotations
import threading
import customtkinter as ctk
from PIL import Image, ImageTk

from services.patient_service  import PatientService
from services.session_service  import SessionService
from services.barcode_service  import STICKER_SIZES, DEFAULT_SIZE
from utils.date_utils import fmt_datetime_be


class StickerPage(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color="transparent")
        self._ctrl    = controller
        self._psvc    = PatientService()
        self._ssvc    = SessionService()
        self._patients: list[dict] = []
        self._checks:   dict[int, ctk.BooleanVar] = {}   # patient_id → BoolVar
        self._search_job: str | None = None
        self._preview_photo = None   # keep reference so GC doesn't collect it

        self._build()
        self.after(200, self.refresh)

    # ─── layout ───────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_topbar()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Left: patient table
        left = ctk.CTkFrame(body, fg_color="white", corner_radius=12,
                            border_width=1, border_color="#dde3ec")
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self._build_table(left)

        # Right: preview + single-print (fixed 240 px)
        right = ctk.CTkFrame(body, fg_color="white", corner_radius=12,
                             border_width=1, border_color="#dde3ec", width=240)
        right.pack(side="left", fill="y")
        right.pack_propagate(False)
        self._build_preview_panel(right)

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=60)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="🏷️  พิมพ์สติ๊กเกอร์ — Barcode Stickers",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", padx=20)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=16)

        # Batch print button
        self._btn_batch = ctk.CTkButton(
            right, text="🖨️  พิมพ์ที่เลือก (0)",
            width=180, height=32,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            state="disabled",
            command=self._batch_print,
        )
        self._btn_batch.pack(side="right", padx=(6, 0))

        # Select-all checkbox
        self._var_all = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            right, text="เลือกทั้งหมด",
            variable=self._var_all,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._toggle_all,
        ).pack(side="right", padx=(6, 0))

        # Session filter
        self._sessions: list[dict] = []
        self._session_filter_map: dict[str, int | None] = {"ทั้งหมด": None}
        self._session_menu = ctk.CTkOptionMenu(
            right, width=220, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            values=["ทั้งหมด"],
            command=self._on_filter_change,
        )
        self._session_menu.pack(side="right", padx=6)
        ctk.CTkLabel(right, text="Session:",
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="right")

        # Search
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(
            right, textvariable=self._search_var,
            placeholder_text="🔍  ค้นหา ชื่อ / HN / บัตรประชาชน",
            width=240, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        ).pack(side="right", padx=6)

    def _build_table(self, card) -> None:
        self._lbl_count = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#78909c",
        )
        self._lbl_count.pack(anchor="e", padx=16, pady=(8, 0))

        COLS = [
            ("☑",           36),
            ("#",            44),
            ("HN",          140),
            ("ชื่อ-นามสกุล", 220),
            ("แผนก",         130),
            ("คิว",          60),
            ("",             80),
        ]
        hdr = ctk.CTkFrame(card, fg_color="#eef2f7", corner_radius=0, height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for i, (text, width) in enumerate(COLS):
            ctk.CTkLabel(
                hdr, text=text, width=width, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#37474f",
            ).pack(side="left", padx=(14 if i == 0 else 6, 0))

        self._body = ctk.CTkScrollableFrame(card, fg_color="white", corner_radius=0)
        self._body.pack(fill="both", expand=True)

    def _build_preview_panel(self, panel) -> None:
        ctk.CTkLabel(
            panel, text="ตัวอย่างสติ๊กเกอร์",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#0f2744",
        ).pack(pady=(14, 4))

        # ── Size selector ──────────────────────────────────────────────────
        ctk.CTkLabel(
            panel, text="ขนาดสติ๊กเกอร์",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#37474f",
        ).pack()

        self._size_var = ctk.StringVar(value=DEFAULT_SIZE)
        ctk.CTkOptionMenu(
            panel,
            variable=self._size_var,
            values=list(STICKER_SIZES.keys()),
            width=210, height=30,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._on_size_change,
        ).pack(padx=12, pady=(2, 8))

        ctk.CTkFrame(panel, height=1, fg_color="#dde3ec").pack(fill="x", padx=12, pady=(0, 6))

        # ── Preview image ──────────────────────────────────────────────────
        self._preview_lbl = ctk.CTkLabel(panel, text="")
        self._preview_lbl.pack(padx=12, pady=4)

        self._preview_info = ctk.CTkLabel(
            panel, text="คลิกแถวผู้ป่วย\nเพื่อดูตัวอย่าง",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#b0bec5", justify="center",
        )
        self._preview_info.pack(pady=4)

        ctk.CTkFrame(panel, height=1, fg_color="#dde3ec").pack(fill="x", padx=12, pady=6)

        self._btn_single = ctk.CTkButton(
            panel, text="🖨️  พิมพ์สติ๊กเกอร์นี้",
            height=38,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            state="disabled",
            command=self._single_print,
        )
        self._btn_single.pack(fill="x", padx=12, pady=(0, 8))

        self._lbl_status = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            wraplength=200, justify="center",
        )
        self._lbl_status.pack(padx=8)

        self._selected_patient: dict | None = None

    # ─── data ─────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        # Reload session list
        sessions = self._ssvc.get_all_sessions()
        self._session_filter_map = {"ทั้งหมด": None}
        for s in sessions:
            label = f"{s['session_code']}  —  {s['session_date']}"
            self._session_filter_map[label] = s["id"]
        self._session_menu.configure(values=list(self._session_filter_map.keys()))

        self._load_patients()

    def _load_patients(self) -> None:
        term       = self._search_var.get().strip() if hasattr(self, "_search_var") else ""
        sel        = self._session_menu.get() if hasattr(self, "_session_menu") else "ทั้งหมด"
        session_id = self._session_filter_map.get(sel)
        self._patients = self._psvc.search(term, session_id)
        self._render()

    def _on_search(self, *_) -> None:
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(350, self._load_patients)

    def _on_filter_change(self, _val: str) -> None:
        self._load_patients()

    # ─── render ───────────────────────────────────────────────────────────

    def _render(self) -> None:
        for w in self._body.winfo_children():
            w.destroy()
        self._checks.clear()

        self._lbl_count.configure(text=f"พบ {len(self._patients)} ราย")

        if not self._patients:
            ctk.CTkLabel(
                self._body,
                text="ไม่พบผู้ป่วย",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#b0bec5",
            ).pack(pady=40)
            self._update_batch_btn()
            return

        for i, p in enumerate(self._patients):
            bg  = "white" if i % 2 == 0 else "#f7f9fc"
            row = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, height=44)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Checkbox
            var = ctk.BooleanVar(value=False)
            self._checks[p["id"]] = var
            ctk.CTkCheckBox(
                row, text="", variable=var, width=36,
                command=self._update_batch_btn,
            ).pack(side="left", padx=(10, 0))

            # Row number
            ctk.CTkLabel(
                row, text=str(i + 1), width=44,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#90a4ae", anchor="w",
            ).pack(side="left", padx=(4, 0))

            # HN (clickable for preview)
            hn_btn = ctk.CTkButton(
                row, text=p["hn"], width=140, anchor="w",
                fg_color="transparent", hover_color="#eef2f7",
                text_color="#1a6bb5",
                font=ctk.CTkFont(family="Courier New", size=15, weight="bold"),
                command=lambda pt=p: self._show_preview(pt),
            )
            hn_btn.pack(side="left", padx=(4, 0))

            # Name (AngsanaUPC)
            ctk.CTkLabel(
                row, text=f"{p['first_name']} {p['last_name']}", width=220,
                font=ctk.CTkFont(family="AngsanaUPC", size=18, weight="bold"),
                text_color="#212121", anchor="w",
            ).pack(side="left", padx=(4, 0))

            # Department
            ctk.CTkLabel(
                row, text=(p.get("department") or "—"), width=130,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#546e7a", anchor="w",
            ).pack(side="left", padx=(4, 0))

            # Queue no (shown when filtered by session)
            q_no = p.get("queue_no")
            ctk.CTkLabel(
                row, text=(str(q_no) if q_no else "—"), width=60,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#37474f", anchor="center",
            ).pack(side="left", padx=(4, 0))

            # Individual print
            ctk.CTkButton(
                row, text="🖨️", width=36, height=28,
                fg_color="#e3eaf4", hover_color="#c5d5e8",
                text_color="#0f2744", font=ctk.CTkFont(size=16, weight="bold"),
                command=lambda pt=p: self._quick_print(pt),
            ).pack(side="left", padx=(4, 6))

            ctk.CTkFrame(self._body, height=1, fg_color="#f0f0f0").pack(fill="x")

        self._update_batch_btn()

    # ─── selection ────────────────────────────────────────────────────────

    def _toggle_all(self) -> None:
        state = self._var_all.get()
        for var in self._checks.values():
            var.set(state)
        self._update_batch_btn()

    def _update_batch_btn(self) -> None:
        n = sum(1 for v in self._checks.values() if v.get())
        self._btn_batch.configure(
            text=f"🖨️  พิมพ์ที่เลือก ({n})",
            state="normal" if n > 0 else "disabled",
        )

    def _selected_patients(self) -> list[dict]:
        ids = {pid for pid, var in self._checks.items() if var.get()}
        return [p for p in self._patients if p["id"] in ids]

    # ─── size helpers ─────────────────────────────────────────────────────

    def _size_mm(self) -> tuple[float, float]:
        """Return (width_mm, height_mm) for the currently selected sticker size."""
        return STICKER_SIZES.get(self._size_var.get(), (40.0, 20.0))

    def _on_size_change(self, _val: str) -> None:
        if self._selected_patient:
            self._show_preview(self._selected_patient)

    # ─── preview ──────────────────────────────────────────────────────────

    def _show_preview(self, patient: dict) -> None:
        self._selected_patient = patient
        self._preview_info.configure(text="")
        self._btn_single.configure(state="normal")

        w_mm, h_mm = self._size_mm()

        def _work():
            from services.barcode_service import generate_label
            full_name = f"{patient['first_name']} {patient['last_name']}"
            img = generate_label(
                patient["hn"], full_name,
                gender=patient.get("gender"),
                date_of_birth=patient.get("date_of_birth"),
                queue_no=patient.get("queue_no"),
                label_w_mm=w_mm,
                label_h_mm=h_mm,
            )
            # Scale to fit preview panel (width ~210 px)
            scale = 210 / img.width
            preview = img.resize(
                (int(img.width * scale), int(img.height * scale)), Image.LANCZOS
            )
            photo = ImageTk.PhotoImage(preview)
            self.after(0, lambda: self._set_preview(photo, patient["hn"]))

        threading.Thread(target=_work, daemon=True).start()

    def _set_preview(self, photo, hn: str) -> None:
        self._preview_photo = photo   # prevent GC
        self._preview_lbl.configure(image=photo, text="")
        self._preview_info.configure(
            text=hn,
            font=ctk.CTkFont(family="Courier New", size=13, weight="bold"),
            text_color="#1a6bb5",
        )

    # ─── print ────────────────────────────────────────────────────────────

    def _quick_print(self, patient: dict) -> None:
        self._show_preview(patient)
        self._do_print_one(patient)

    def _single_print(self) -> None:
        if self._selected_patient:
            self._do_print_one(self._selected_patient)

    def _do_print_one(self, patient: dict) -> None:
        from services.barcode_service import print_label
        full_name = f"{patient['first_name']} {patient['last_name']}"
        w_mm, h_mm = self._size_mm()
        try:
            print_label(
                patient["hn"], full_name,
                gender=patient.get("gender"),
                date_of_birth=patient.get("date_of_birth"),
                queue_no=patient.get("queue_no"),
                label_w_mm=w_mm,
                label_h_mm=h_mm,
            )
            self._set_status("✅  ส่งพิมพ์แล้ว", "#2e7d32")
        except Exception as exc:
            self._set_status(f"❌  {exc}", "#c62828")

    def _batch_print(self) -> None:
        selected = self._selected_patients()
        if not selected:
            return
        self._btn_batch.configure(state="disabled", text="กำลังสร้าง PDF…")

        w_mm, h_mm = self._size_mm()

        def _work():
            from services.barcode_service import generate_batch_pdf
            import os
            try:
                path = generate_batch_pdf(selected, label_w_mm=w_mm, label_h_mm=h_mm)
                os.startfile(path)
                self.after(0, lambda: self._set_status(
                    f"✅  เปิด PDF แล้ว ({len(selected)} แผ่น)\nสั่งพิมพ์จาก PDF viewer", "#2e7d32"
                ))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"❌  {exc}", "#c62828"))
            finally:
                self.after(0, self._update_batch_btn)

        threading.Thread(target=_work, daemon=True).start()

    def _set_status(self, msg: str, color: str) -> None:
        self._lbl_status.configure(text=msg, text_color=color)
        self.after(5000, lambda: self._lbl_status.configure(text=""))
