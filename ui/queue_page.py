"""Queue & Check-in page — USB scanner zone + manual queue management."""
from __future__ import annotations
import customtkinter as ctk
from services.queue_service import (
    QueueService, OK, NOT_FOUND, NOT_ENROLLED, ALREADY_DONE, ALREADY_COMPLETE
)
from services.audit_service import AuditService
from utils.date_utils import fmt_date_be, fmt_datetime_be

_TABS = [
    ("all",        "ทั้งหมด",    "#455a64"),
    ("pending",    "รอตรวจ",     "#f57c00"),
    ("checked_in", "เช็กอินแล้ว","#2e7d32"),
    ("done",       "เสร็จสิ้น",  "#1565c0"),
    ("absent",     "ไม่มา",      "#c62828"),
]

_STATUS_LABEL = {
    "pending":    "รอตรวจ",
    "checked_in": "เช็กอิน ✓",
    "done":       "เสร็จสิ้น",
    "absent":     "ไม่มา",
}
_STATUS_COLOR = {
    "pending":    "#f57c00",
    "checked_in": "#2e7d32",
    "done":       "#1565c0",
    "absent":     "#c62828",
}

# All available status transitions (key = button label, value = target status)
_ALL_STATUSES = [
    ("รอตรวจ",    "pending",    "#f57c00"),
    ("เช็กอิน",   "checked_in", "#2e7d32"),
    ("เสร็จสิ้น", "done",       "#1565c0"),
    ("ไม่มา",     "absent",     "#c62828"),
]


class QueuePage(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color="transparent")
        self._ctrl        = controller
        self._svc         = QueueService()
        self._audit       = AuditService()
        self._filter      = "all"
        self._scan_mode   = False

        self._build()
        self.after(200, self.refresh)

    # ─── build ────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_topbar()
        self._build_scanner_zone()
        self._build_stats_bar()
        self._build_filter_tabs()
        self._build_table()

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="📋  คิวตรวจ — Queue Management",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", padx=20)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=16)

        self._btn_scan_mode = ctk.CTkButton(
            right, text="📷  เปิด Scan Mode",
            width=160, height=34,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._toggle_scan_mode,
        )
        self._btn_scan_mode.pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            right, text="🔄  รีเฟรช",
            width=100, height=34,
            fg_color="#455a64", hover_color="#37474f",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self.refresh,
        ).pack(side="right", padx=6)

    def _build_scanner_zone(self) -> None:
        self._scan_zone = ctk.CTkFrame(
            self, fg_color="#1a3a5c", corner_radius=0, height=0
        )

        inner = ctk.CTkFrame(self._scan_zone, fg_color="transparent")
        inner.pack(pady=8)

        # ── Mode selector ──────────────────────────────────────────────
        mode_row = ctk.CTkFrame(inner, fg_color="transparent")
        mode_row.pack(pady=(0, 6))

        ctk.CTkLabel(
            mode_row, text="โหมดสแกน:",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#aac8e4",
        ).pack(side="left", padx=(0, 10))

        self._scan_action = ctk.StringVar(value="check_in")

        ctk.CTkRadioButton(
            mode_row, text="📥  เช็กอิน",
            variable=self._scan_action, value="check_in",
            fg_color="#2e7d32",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#e0f2f1",
            command=self._update_scan_btn,
        ).pack(side="left", padx=(0, 24))

        ctk.CTkRadioButton(
            mode_row, text="✅  เสร็จสิ้น (Complete)",
            variable=self._scan_action, value="complete",
            fg_color="#1565c0",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#e3f2fd",
            command=self._update_scan_btn,
        ).pack(side="left")

        # ── Entry row ──────────────────────────────────────────────────
        ctk.CTkLabel(
            inner, text="🔍  สแกนบาร์โค้ด หรือพิมพ์ HN / เลขบัตร (กด Enter เพื่อยืนยัน)",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#aac8e4",
        ).pack()

        entry_row = ctk.CTkFrame(inner, fg_color="transparent")
        entry_row.pack(pady=6)

        self._scan_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="สแกนหรือพิมพ์ที่นี่…",
            width=320, height=42,
            font=ctk.CTkFont(family="Courier New", size=17, weight="bold"),
        )
        self._scan_entry.pack(side="left", padx=(0, 8))
        self._scan_entry.bind("<Return>", self._on_scan)

        self._btn_scan_action = ctk.CTkButton(
            entry_row, text="✔  เช็กอิน",
            width=148, height=42,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            command=self._on_scan,
        )
        self._btn_scan_action.pack(side="left")

        self._lbl_scan_result = ctk.CTkLabel(
            inner, text="",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        )
        self._lbl_scan_result.pack(pady=(0, 4))

    def _build_stats_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="#eef5ff", corner_radius=0, height=48)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(side="left", padx=20, pady=6)

        self._stat_chips: dict[str, ctk.CTkLabel] = {}
        specs = [
            ("total",   "ทั้งหมด",  "#455a64"),
            ("arrived", "มาแล้ว",   "#1565c0"),
            ("pending", "รอตรวจ",   "#f57c00"),
            ("absent",  "ไม่มา",    "#c62828"),
        ]
        for key, label, color in specs:
            chip = ctk.CTkFrame(inner, fg_color=color, corner_radius=8)
            chip.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(
                chip, text=label,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="white",
            ).pack(side="left", padx=(10, 4), pady=4)
            val_lbl = ctk.CTkLabel(
                chip, text="—",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="white",
            )
            val_lbl.pack(side="left", padx=(0, 10), pady=4)
            self._stat_chips[key] = val_lbl

    def _build_filter_tabs(self) -> None:
        self._tab_bar = ctk.CTkFrame(self, fg_color="#eef2f7", corner_radius=0, height=46)
        self._tab_bar.pack(fill="x")
        self._tab_bar.pack_propagate(False)
        self._tab_btns: dict[str, ctk.CTkButton] = {}

        for key, label, color in _TABS:
            btn = ctk.CTkButton(
                self._tab_bar,
                text=label,
                width=120, height=34,
                corner_radius=6,
                fg_color=color if key == self._filter else "transparent",
                hover_color=color,
                text_color="white" if key == self._filter else "#37474f",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                command=lambda k=key: self._set_filter(k),
            )
            btn.pack(side="left", padx=(8, 0), pady=6)
            self._tab_btns[key] = btn

    def _build_table(self) -> None:
        card = ctk.CTkFrame(
            self, fg_color="white", corner_radius=12,
            border_width=1, border_color="#dde3ec",
        )
        card.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self._lbl_count = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#78909c",
        )
        self._lbl_count.pack(anchor="e", padx=16, pady=(8, 0))

        COLS = [
            ("#",              44),
            ("คิว",            60),
            ("HN",            130),
            ("ชื่อ",          130),
            ("นามสกุล",       150),
            ("วันเดือนปีเกิด", 130),
            ("สถานะ",          130),
            ("เช็กอินเมื่อ",   160),
            ("เปลี่ยนสถานะ",   290),
        ]
        hdr = ctk.CTkFrame(card, fg_color="#eef2f7", corner_radius=0, height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for i, (text, width) in enumerate(COLS):
            ctk.CTkLabel(
                hdr, text=text, width=width, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#37474f",
            ).pack(side="left", padx=(14 if i == 0 else 8, 0))

        self._body = ctk.CTkScrollableFrame(card, fg_color="white", corner_radius=0)
        self._body.pack(fill="both", expand=True)

    # ─── scan mode ────────────────────────────────────────────────────────

    def _update_scan_btn(self) -> None:
        if self._scan_action.get() == "complete":
            self._btn_scan_action.configure(
                text="✅  เสร็จสิ้น",
                fg_color="#1565c0", hover_color="#0d47a1",
            )
        else:
            self._btn_scan_action.configure(
                text="✔  เช็กอิน",
                fg_color="#2e7d32", hover_color="#1b5e20",
            )

    def _toggle_scan_mode(self) -> None:
        self._scan_mode = not self._scan_mode
        if self._scan_mode:
            self._scan_zone.pack(fill="x", after=self._scan_zone.master.winfo_children()[0])
            self._scan_zone.configure(height=185)
            self._btn_scan_mode.configure(
                text="✖  ปิด Scan Mode", fg_color="#c62828", hover_color="#b71c1c"
            )
            self._scan_entry.focus_set()
        else:
            self._scan_zone.pack_forget()
            self._btn_scan_mode.configure(
                text="📷  เปิด Scan Mode", fg_color="#1a6bb5", hover_color="#155a9a"
            )

    def _on_scan(self, _event=None) -> None:
        session = self._ctrl.get_current_session()
        if not session:
            self._show_scan_result("⚠  ไม่มี Session ที่เปิดอยู่", "#f57c00")
            return

        identifier = self._scan_entry.get().strip()
        if not identifier:
            return

        mode = self._scan_action.get()
        if mode == "complete":
            result = self._svc.scan_complete(identifier, session["id"], self._ctrl._user["id"])
        else:
            result = self._svc.check_in(identifier, session["id"], self._ctrl._user["id"])

        status  = result["status"]
        patient = result.get("patient")
        name    = f"{patient['first_name']} {patient['last_name']}" if patient else ""

        if status == OK:
            user = self._ctrl._user
            if mode == "complete":
                self._show_scan_result(f"✅  เสร็จสิ้นแล้ว — {name}", "#1565c0")
                self._audit.log(user["id"], user["full_name"], "COMPLETE",
                                f"{name}  ผ่านสแกน")
            else:
                self._show_scan_result(f"✅  เช็กอินสำเร็จ — {name}", "#2e7d32")
                self._audit.log(user["id"], user["full_name"], "CHECK_IN",
                                f"{name}  ผ่านสแกน")
        elif status == NOT_FOUND:
            self._show_scan_result(f"❌  ไม่พบผู้ป่วย: {identifier}", "#c62828")
        elif status == NOT_ENROLLED:
            self._show_scan_result(f"⚠  ไม่ได้ลงทะเบียนใน Session นี้ — {name}", "#f57c00")
        elif status == ALREADY_DONE:
            ts = result.get("checked_in_at") or ""
            self._show_scan_result(f"ℹ  เช็กอินแล้ว ({ts}) — {name}", "#1565c0")
        elif status == ALREADY_COMPLETE:
            self._show_scan_result(f"ℹ  เสร็จสิ้นแล้ว — {name}", "#1565c0")

        self._scan_entry.delete(0, "end")
        self._scan_entry.focus_set()
        self.refresh()

    def _show_scan_result(self, msg: str, color: str) -> None:
        self._lbl_scan_result.configure(text=msg, text_color=color)
        self.after(4000, lambda: self._lbl_scan_result.configure(text=""))

    # ─── filter ───────────────────────────────────────────────────────────

    def _set_filter(self, key: str) -> None:
        self._filter = key
        for k, btn in self._tab_btns.items():
            color = dict(_TABS)[k]
            btn.configure(
                fg_color=color if k == key else "transparent",
                text_color="white" if k == key else "#37474f",
            )
        self.refresh()

    # ─── data ─────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        session = self._ctrl.get_current_session()
        if not session:
            self._lbl_count.configure(text="ยังไม่มี Session ที่เปิดอยู่")
            self._update_stats_chips({})
            self._render([], session)
            return

        rows  = self._svc.get_queue(session["id"], self._filter)
        stats = self._svc.get_stats(session["id"])

        self._update_stats_chips(stats)

        for key, label, _ in _TABS:
            count = stats.get(key, 0)
            self._tab_btns[key].configure(text=f"{label}  ({count})")

        self._lbl_count.configure(text=f"แสดง {len(rows)} รายการ")
        self._render(rows, session)
        if self._scan_mode:
            self.after(50, self._scan_entry.focus_set)

    def _update_stats_chips(self, stats: dict) -> None:
        arrived = stats.get("checked_in", 0) + stats.get("done", 0)
        self._stat_chips["total"].configure(text=str(stats.get("total", "—")))
        self._stat_chips["arrived"].configure(text=str(arrived if stats else "—"))
        self._stat_chips["pending"].configure(text=str(stats.get("pending", "—")))
        self._stat_chips["absent"].configure(text=str(stats.get("absent", "—")))

    # ─── render ───────────────────────────────────────────────────────────

    def _render(self, rows: list[dict], session) -> None:
        for w in self._body.winfo_children():
            w.destroy()

        if not rows:
            msg = "ยังไม่มีผู้ป่วยในคิว" if not session else "ไม่มีรายการในกลุ่มนี้"
            ctk.CTkLabel(
                self._body, text=msg,
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#b0bec5",
            ).pack(pady=50)
            return

        for i, r in enumerate(rows):
            bg  = "white" if i % 2 == 0 else "#f7f9fc"
            row = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, height=48)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Row number
            ctk.CTkLabel(
                row, text=str(i + 1), width=44,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#90a4ae", anchor="w",
            ).pack(side="left", padx=(14, 0))

            # Queue no
            ctk.CTkLabel(
                row, text=str(r["queue_no"]), width=60,
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#37474f", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # HN
            ctk.CTkLabel(
                row, text=r["hn"], width=130,
                font=ctk.CTkFont(family="Courier New", size=15, weight="bold"),
                text_color="#1a6bb5", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # First name
            ctk.CTkLabel(
                row, text=r["first_name"], width=130,
                font=ctk.CTkFont(family="AngsanaUPC", size=18, weight="bold"),
                text_color="#212121", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Last name
            ctk.CTkLabel(
                row, text=r["last_name"], width=150,
                font=ctk.CTkFont(family="AngsanaUPC", size=18, weight="bold"),
                text_color="#212121", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Date of birth
            dob = fmt_date_be(r.get("date_of_birth"))
            ctk.CTkLabel(
                row, text=dob, width=130,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#546e7a", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Status badge
            st    = r["status"]
            color = _STATUS_COLOR.get(st, "#78909c")
            badge = ctk.CTkFrame(row, fg_color=color, corner_radius=6, width=110, height=28)
            badge.pack(side="left", padx=(8, 0))
            badge.pack_propagate(False)
            ctk.CTkLabel(
                badge, text=_STATUS_LABEL.get(st, st),
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="white",
            ).place(relx=0.5, rely=0.5, anchor="center")

            # Checked-in time (BE)
            ts = fmt_datetime_be(r.get("checked_in_at")) if r.get("checked_in_at") else "—"
            ctk.CTkLabel(
                row, text=ts[:16], width=160,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#78909c", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Status change buttons — all 4, current is highlighted/disabled
            act = ctk.CTkFrame(row, fg_color="transparent")
            act.pack(side="left", padx=(6, 4))

            for lbl, target, btn_color in _ALL_STATUSES:
                is_current = (st == target)
                ctk.CTkButton(
                    act, text=lbl,
                    width=62, height=28,
                    fg_color=btn_color if is_current else "#e8edf2",
                    hover_color=btn_color,
                    text_color="white" if is_current else "#455a64",
                    font=ctk.CTkFont(family="Segoe UI", size=13,
                                     weight="bold" if is_current else "normal"),
                    state="disabled" if is_current else "normal",
                    command=lambda pid=r["patient_id"], ns=target: self._change_status(pid, ns),
                ).pack(side="left", padx=(0, 3))

            ctk.CTkFrame(self._body, height=1, fg_color="#f0f0f0").pack(fill="x")

    # ─── actions ──────────────────────────────────────────────────────────

    def _change_status(self, patient_id: int, new_status: str) -> None:
        session = self._ctrl.get_current_session()
        if not session:
            return
        self._svc.update_status(patient_id, session["id"], new_status, self._ctrl._user["id"])
        user = self._ctrl._user
        self._audit.log(user["id"], user["full_name"], "CHANGE_STATUS",
                        f"patient_id:{patient_id}  →  {new_status}")
        self.refresh()
