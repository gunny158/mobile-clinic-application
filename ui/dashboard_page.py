from __future__ import annotations
from datetime import datetime
import customtkinter as ctk
from services.session_service import SessionService
from utils.date_utils import fmt_time, fmt_datetime_be, today_be_long

_STATUS_COLOR = {
    "pending":    "#f57c00",
    "checked_in": "#2e7d32",
    "done":       "#1565c0",
    "absent":     "#c62828",
}
_STATUS_LABEL = {
    "pending":    "รอตรวจ",
    "checked_in": "ตรวจแล้ว ✓",
    "done":       "เสร็จสิ้น",
    "absent":     "ไม่มา",
}


class DashboardPage(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color="transparent")
        self._ctrl = controller
        self._svc = SessionService()
        self._sessions: list[dict] = []
        self._session_map: dict[str, dict] = {}
        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        self._refresh_job: str | None = None

        self._build()
        self.after(150, self._load_sessions)

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        self._build_topbar()
        self._build_stats_row()
        self._build_table()

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="📊  Dashboard — หน้าหลัก",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", padx=20, pady=0)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=16)

        ctk.CTkLabel(
            right,
            text=f"📅  {today_be_long()}",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#607d8b",
        ).pack(side="right", padx=(12, 0))

        ctk.CTkButton(
            right, text="🔄", width=36, height=32,
            fg_color="#e3eaf4", hover_color="#c5d5e8",
            text_color="#0f2744", font=ctk.CTkFont(size=17, weight="bold"),
            command=self.refresh,
        ).pack(side="right", padx=4)

        self._dropdown = ctk.CTkOptionMenu(
            right, width=300, height=32,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color="#1a6bb5", button_color="#155a9a",
            values=["กำลังโหลด…"],
            command=self._on_session_change,
        )
        self._dropdown.pack(side="right", padx=4)

        ctk.CTkLabel(
            right, text="Session :",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#0f2744",
        ).pack(side="right", padx=(0, 4))

        self._btn_delete = ctk.CTkButton(
            right, text="🗑️",
            width=36, height=32,
            fg_color="#e53935", hover_color="#c62828",
            text_color="white",
            font=ctk.CTkFont(size=17, weight="bold"),
            command=self._delete_session,
        )
        self._btn_delete.pack(side="right", padx=(0, 4))

        ctk.CTkButton(
            right, text="➕  Session ใหม่",
            width=140, height=32,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._open_new_session,
        ).pack(side="right", padx=(0, 6))

    def _build_stats_row(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(14, 8))
        row.columnconfigure((0, 1, 2, 3), weight=1, uniform="c")

        specs = [
            ("total",      "ผู้ป่วยทั้งหมด", "#455a64"),
            ("pending",    "รอตรวจ",          "#f57c00"),
            ("checked_in", "ตรวจแล้ว",        "#2e7d32"),
            ("done",       "เสร็จสิ้น",       "#1565c0"),
        ]
        for col, (key, title, color) in enumerate(specs):
            card = ctk.CTkFrame(
                row, fg_color="white", corner_radius=12,
                border_width=1, border_color="#dde3ec",
            )
            card.grid(row=0, column=col, padx=6, sticky="nsew", ipady=4)

            ctk.CTkFrame(card, height=5, fg_color=color, corner_radius=0).pack(fill="x")

            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#78909c",
            ).pack(pady=(12, 2))

            lbl = ctk.CTkLabel(
                card, text="—",
                font=ctk.CTkFont(family="Segoe UI", size=44, weight="bold"),
                text_color=color,
            )
            lbl.pack(pady=(2, 14))
            self._stat_labels[key] = lbl

    def _build_table(self) -> None:
        card = ctk.CTkFrame(
            self, fg_color="white", corner_radius=12,
            border_width=1, border_color="#dde3ec",
        )
        card.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        tbar = ctk.CTkFrame(card, fg_color="transparent", height=44)
        tbar.pack(fill="x", padx=16)
        tbar.pack_propagate(False)

        ctk.CTkLabel(
            tbar, text="รายชื่อผู้ป่วย",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", pady=8)

        self._lbl_updated = ctk.CTkLabel(
            tbar, text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#b0bec5",
        )
        self._lbl_updated.pack(side="right", pady=8)

        COLS = [
            ("#",          44,  "#37474f"),
            ("คิว",        52,  "#37474f"),
            ("HN",        130, "#37474f"),
            ("ชื่อ-นามสกุล", 0, "#37474f"),
            ("สถานะ",     120, "#37474f"),
            ("เวลาเช็คอิน", 120, "#37474f"),
        ]
        hdr = ctk.CTkFrame(card, fg_color="#eef2f7", corner_radius=0, height=34)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        for i, (text, width, color) in enumerate(COLS):
            padx = (16, 0) if i == 0 else (8, 0)
            kw = {"width": width} if width else {}
            ctk.CTkLabel(
                hdr, text=text,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color=color, anchor="w", **kw,
            ).pack(side="left", padx=padx)

        self._body = ctk.CTkScrollableFrame(card, fg_color="white", corner_radius=0)
        self._body.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ data

    def _load_sessions(self) -> None:
        self._sessions = self._svc.get_active_sessions()
        if not self._sessions:
            self._dropdown.configure(values=["— ยังไม่มี Session —"])
            self._dropdown.set("— ยังไม่มี Session —")
            self._ctrl.set_current_session(None)
            return

        labels = [
            f"{s['session_code']}  —  {s['session_name']}"
            for s in self._sessions
        ]
        self._session_map = dict(zip(labels, self._sessions))
        self._dropdown.configure(values=labels)
        self._dropdown.set(labels[0])
        self._on_session_change(labels[0])

    def _on_session_change(self, label: str) -> None:
        session = self._session_map.get(label)
        self._ctrl.set_current_session(session)
        self.refresh()

    def refresh(self) -> None:
        if self._refresh_job:
            self.after_cancel(self._refresh_job)

        session = self._ctrl.get_current_session()
        if session:
            stats = self._svc.get_session_stats(session["id"])
            self._update_stats(stats)
            self._update_table(self._svc.get_patients(session["id"]))
        else:
            for lbl in self._stat_labels.values():
                lbl.configure(text="—")
            self._clear_body()

        self._lbl_updated.configure(
            text=f"อัปเดต {datetime.now().strftime('%H:%M:%S')}"
        )
        self._refresh_job = self.after(30_000, self.refresh)

    # ------------------------------------------------------------------ render

    def _update_stats(self, stats: dict) -> None:
        for key, lbl in self._stat_labels.items():
            lbl.configure(text=str(stats.get(key, 0)))

    def _clear_body(self) -> None:
        for w in self._body.winfo_children():
            w.destroy()

    def _update_table(self, patients: list[dict]) -> None:
        self._clear_body()

        if not patients:
            ctk.CTkLabel(
                self._body,
                text="ยังไม่มีผู้ป่วยใน Session นี้\nลองเพิ่มผู้ป่วยจากเมนู 'ข้อมูลผู้ป่วย'",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#b0bec5",
                justify="center",
            ).pack(pady=52)
            return

        for i, p in enumerate(patients):
            bg = "white" if i % 2 == 0 else "#f7f9fc"
            row = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, height=42)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Row number
            ctk.CTkLabel(
                row, text=str(i + 1), width=44,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#90a4ae", anchor="w",
            ).pack(side="left", padx=(16, 0))

            # Queue number
            ctk.CTkLabel(
                row, text=str(p["queue_no"] or "—"), width=52,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#546e7a", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # HN
            ctk.CTkLabel(
                row, text=p["hn"], width=130,
                font=ctk.CTkFont(family="Courier New", size=15, weight="bold"),
                text_color="#1a6bb5", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Full name
            name_lbl = ctk.CTkLabel(
                row,
                text=f"{p['first_name']}  {p['last_name']}",
                font=ctk.CTkFont(family="AngsanaUPC", size=18, weight="bold"),
                text_color="#212121", anchor="w",
            )
            name_lbl.pack(side="left", padx=(8, 0), fill="x", expand=True)

            # Status badge
            status = p["status"]
            color  = _STATUS_COLOR.get(status, "#78909c")
            badge  = ctk.CTkFrame(row, fg_color=color, corner_radius=6, width=92, height=26)
            badge.pack(side="left", padx=8)
            badge.pack_propagate(False)
            ctk.CTkLabel(
                badge,
                text=_STATUS_LABEL.get(status, status),
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="white",
            ).place(relx=0.5, rely=0.5, anchor="center")

            # Check-in time (BE)
            ctk.CTkLabel(
                row, text=fmt_time(p["checked_in_at"]) if p["checked_in_at"] else "—",
                width=120,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#78909c", anchor="w",
            ).pack(side="left", padx=(8, 0))

            ctk.CTkFrame(self._body, height=1, fg_color="#f0f0f0").pack(fill="x")

    # ------------------------------------------------------------------ dialog

    def _delete_session(self) -> None:
        from tkinter import messagebox
        session = self._ctrl.get_current_session()
        if not session:
            return
        if not messagebox.askyesno(
            "ลบ Session",
            f"ลบ Session:\n{session['session_code']} — {session['session_name']}\n\nข้อมูลคิวผู้ป่วยทั้งหมดใน Session นี้จะถูกลบด้วย\n\nยืนยัน?",
        ):
            return
        self._svc.delete_session(session["id"])
        self._ctrl.set_current_session(None)
        self._load_sessions()

    def _open_new_session(self) -> None:
        NewSessionDialog(self, user_id=self._ctrl._user["id"],
                         on_created=self._on_session_created)

    def _on_session_created(self, session: dict) -> None:
        label = f"{session['session_code']}  —  {session['session_name']}"
        self._session_map[label] = session
        values = list(self._session_map.keys())
        self._dropdown.configure(values=values)
        self._dropdown.set(label)
        self._on_session_change(label)


# ══════════════════════════════════════════════════════════════════════════════
# New Session Dialog
# ══════════════════════════════════════════════════════════════════════════════

class NewSessionDialog(ctk.CTkToplevel):
    def __init__(self, parent, user_id: int, on_created) -> None:
        super().__init__(parent)
        self._svc = SessionService()
        self._user_id = user_id
        self._on_created = on_created

        self.title("สร้าง Session ใหม่")
        self.resizable(False, False)
        self.grab_set()
        self._center(460, 430)
        self._build()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="สร้าง Screening Session ใหม่",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
        ).pack(pady=(22, 2))
        ctk.CTkLabel(
            self, text="กำหนดข้อมูล Session ก่อนเริ่มตรวจสุขภาพ",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="gray",
        ).pack(pady=(0, 18))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=36)

        def _field(label: str, placeholder: str, default: str = "") -> ctk.CTkEntry:
            ctk.CTkLabel(
                form, text=label, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            ).pack(fill="x", pady=(8, 2))
            e = ctk.CTkEntry(
                form, placeholder_text=placeholder, height=40,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            )
            if default:
                e.insert(0, default)
            e.pack(fill="x")
            return e

        from datetime import date
        self._e_name     = _field("ชื่อ Session *", "เช่น ตรวจสุขภาพประจำปี ABC 2568")
        self._e_location = _field("สถานที่",        "เช่น บริษัท ABC จำกัด")
        self._e_date     = _field(
            "วันที่ตรวจ (YYYY-MM-DD) *", "YYYY-MM-DD",
            default=date.today().isoformat(),
        )

        self._lbl_err = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#e53935",
        )
        self._lbl_err.pack(pady=(10, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=36, pady=(10, 22))

        ctk.CTkButton(
            btn_row, text="💾  บันทึก Session",
            height=46,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            command=self._submit,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="ยกเลิก",
            height=46, width=100,
            fg_color="#e0e0e0", hover_color="#bdbdbd",
            text_color="#212121",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            command=self.destroy,
        ).pack(side="left")

    def _submit(self) -> None:
        name     = self._e_name.get().strip()
        location = self._e_location.get().strip()
        s_date   = self._e_date.get().strip()

        if not name:
            self._lbl_err.configure(text="⚠  กรุณากรอกชื่อ Session")
            return
        if not s_date:
            self._lbl_err.configure(text="⚠  กรุณากรอกวันที่")
            return

        try:
            session = self._svc.create_session(name, location, s_date, self._user_id)
            self._on_created(session)
            self.destroy()
        except Exception as exc:
            self._lbl_err.configure(text=f"⚠  {exc}")
