from __future__ import annotations
import customtkinter as ctk
from services.patient_service import PatientService
from services.audit_service import AuditService
from utils.date_utils import fmt_date_be

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


def _age(dob_str) -> str:
    try:
        from datetime import date
        dob   = date.fromisoformat(str(dob_str)[:10])
        today = date.today()
        return str(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))
    except Exception:
        return "—"


class PatientsPage(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color="transparent")
        self._ctrl   = controller
        self._svc    = PatientService()
        self._audit  = AuditService()
        self._search_job: str | None = None

        self._build()
        self.after(200, self.refresh)

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        self._build_topbar()
        self._build_stats_bar()
        self._build_table()

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="👥  ข้อมูลผู้ป่วย — Patient Registry",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", padx=20)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=16)

        ctk.CTkButton(
            right, text="📥  Import Excel",
            width=140, height=34,
            fg_color="#455a64", hover_color="#37474f",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._open_import,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            right, text="➕  เพิ่มผู้ป่วย",
            width=130, height=34,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._open_add,
        ).pack(side="right", padx=6)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(
            right,
            textvariable=self._search_var,
            placeholder_text="🔍  ค้นหา ชื่อ / HN / บัตรประชาชน",
            width=280, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).pack(side="right", padx=6)

    def _build_stats_bar(self) -> None:
        self._stats_bar = ctk.CTkFrame(self, fg_color="#f0f4f8", corner_radius=0, height=42)
        self._stats_bar.pack(fill="x")
        self._stats_bar.pack_propagate(False)
        self._lbl_stats = ctk.CTkLabel(
            self._stats_bar, text="",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#37474f",
        )
        self._lbl_stats.pack(side="left", padx=20, pady=8)

    def _build_table(self) -> None:
        card = ctk.CTkFrame(
            self, fg_color="white", corner_radius=12,
            border_width=1, border_color="#dde3ec",
        )
        card.pack(fill="both", expand=True, padx=20, pady=(8, 16))

        self._lbl_count = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#78909c",
        )
        self._lbl_count.pack(anchor="e", padx=16, pady=(8, 0))

        COLS = [
            ("#",              44),
            ("HN",            120),
            ("ชื่อ",          130),
            ("นามสกุล",       150),
            ("วันเดือนปีเกิด", 120),
            ("อายุ",            55),
            ("เพศ",             60),
            ("แผนก",           120),
            ("สถานะ Session",  120),
            ("Actions",        150),
        ]
        hdr = ctk.CTkFrame(card, fg_color="#eef2f7", corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for i, (text, width) in enumerate(COLS):
            padx = (14, 0) if i == 0 else (8, 0)
            ctk.CTkLabel(
                hdr, text=text, width=width, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#37474f",
            ).pack(side="left", padx=padx)

        self._body = ctk.CTkScrollableFrame(card, fg_color="white", corner_radius=0)
        self._body.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ data

    def refresh(self) -> None:
        session    = self._ctrl.get_current_session()
        session_id = session["id"] if session else None
        term       = getattr(self, "_search_var", ctk.StringVar()).get().strip()
        patients   = self._svc.search(term, session_id)
        self._lbl_count.configure(text=f"พบ {len(patients)} รายการ")
        self._update_stats(patients, session_id)
        self._render(patients, session_id)

    def _update_stats(self, patients: list[dict], session_id: int | None) -> None:
        total    = len(patients)
        arrived  = sum(1 for p in patients if p.get("session_status") in ("checked_in", "done"))
        pending  = sum(1 for p in patients if p.get("session_status") == "pending")
        absent   = sum(1 for p in patients if p.get("session_status") == "absent")
        if session_id:
            txt = (
                f"ผู้ป่วยทั้งหมด: {total}  |  "
                f"มาแล้ว: {arrived}  |  "
                f"รอตรวจ: {pending}  |  "
                f"ไม่มา: {absent}"
            )
        else:
            txt = f"ผู้ป่วยทั้งหมดในระบบ: {total} ราย"
        self._lbl_stats.configure(text=txt)

    def _on_search(self, *_) -> None:
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(350, self.refresh)

    # ------------------------------------------------------------------ render

    def _render(self, patients: list[dict], session_id: int | None) -> None:
        for w in self._body.winfo_children():
            w.destroy()

        if not patients:
            ctk.CTkLabel(
                self._body,
                text="ไม่พบข้อมูลผู้ป่วย\nลองค้นหาด้วยคำอื่น หรือเพิ่มผู้ป่วยใหม่",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#b0bec5", justify="center",
            ).pack(pady=50)
            return

        for i, p in enumerate(patients):
            bg  = "white" if i % 2 == 0 else "#f7f9fc"
            row = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, height=52)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Row number
            ctk.CTkLabel(
                row, text=str(i + 1), width=44,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#90a4ae", anchor="w",
            ).pack(side="left", padx=(14, 0))

            # HN
            ctk.CTkLabel(
                row, text=p["hn"], width=120,
                font=ctk.CTkFont(family="Courier New", size=16, weight="bold"),
                text_color="#1a6bb5", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # First name
            ctk.CTkLabel(
                row, text=p["first_name"], width=130,
                font=ctk.CTkFont(family="AngsanaUPC", size=18, weight="bold"),
                text_color="#212121", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Last name
            ctk.CTkLabel(
                row, text=p["last_name"], width=150,
                font=ctk.CTkFont(family="AngsanaUPC", size=18, weight="bold"),
                text_color="#212121", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Date of birth
            dob = fmt_date_be(p.get("date_of_birth"))
            ctk.CTkLabel(
                row, text=dob, width=120,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#546e7a", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Age
            age = _age(p.get("date_of_birth"))
            ctk.CTkLabel(
                row, text=f"{age} ปี", width=55,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#546e7a", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Gender badge
            gender_map = {"M": ("ชาย", "#1565c0"), "F": ("หญิง", "#ad1457"), "Other": ("อื่น", "#546e7a")}
            g_label, g_color = gender_map.get(p.get("gender") or "", ("—", "#9e9e9e"))
            ctk.CTkLabel(
                row, text=g_label, width=60,
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color=g_color, anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Department
            ctk.CTkLabel(
                row, text=(p.get("department") or "—"), width=120,
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#546e7a", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Session status / enrol button
            sess_status = p.get("session_status")
            if not session_id:
                ctk.CTkLabel(row, text="—", width=120,
                             font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                             text_color="#b0bec5", anchor="w").pack(side="left", padx=(8, 0))
            elif sess_status:
                color = _STATUS_COLOR.get(sess_status, "#78909c")
                badge = ctk.CTkFrame(row, fg_color=color, corner_radius=6, width=110, height=26)
                badge.pack(side="left", padx=(8, 0))
                badge.pack_propagate(False)
                ctk.CTkLabel(
                    badge,
                    text=_STATUS_LABEL.get(sess_status, sess_status),
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    text_color="white",
                ).place(relx=0.5, rely=0.5, anchor="center")
            else:
                ctk.CTkButton(
                    row, text="ลงทะเบียน",
                    width=110, height=30,
                    fg_color="#1a6bb5", hover_color="#155a9a",
                    font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                    command=lambda pid=p["id"]: self._enrol(pid, session_id),
                ).pack(side="left", padx=(8, 0))

            # Edit / Delete buttons
            ctk.CTkButton(
                row, text="✏️  แก้ไข",
                width=88, height=30,
                fg_color="#1a6bb5", hover_color="#155a9a",
                text_color="white",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                command=lambda pt=p: self._open_edit(pt),
            ).pack(side="left", padx=(6, 2))

            ctk.CTkButton(
                row, text="🗑️  ลบ",
                width=72, height=30,
                fg_color="#e53935", hover_color="#c62828",
                text_color="white",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                command=lambda pt=p: self._delete_patient(pt),
            ).pack(side="left", padx=(2, 4))

            ctk.CTkFrame(self._body, height=1, fg_color="#f0f0f0").pack(fill="x")

    # ------------------------------------------------------------------ actions

    def _delete_patient(self, patient: dict) -> None:
        from tkinter import messagebox
        name = f"{patient['first_name']} {patient['last_name']}"
        if not messagebox.askyesno(
            "ลบผู้ป่วย",
            f"ลบ: {name}  ({patient['hn']})\n\nข้อมูลคิว, ผลแล็บ และประวัติสุขภาพทั้งหมดจะถูกลบด้วย\n\nยืนยัน?",
        ):
            return
        self._svc.delete(patient["id"])
        user = self._ctrl._user
        self._audit.log(user["id"], user["full_name"], "DELETE_PATIENT",
                        f"HN:{patient['hn']}  {name}")
        self.refresh()

    def _enrol(self, patient_id: int, session_id: int) -> None:
        self._svc.enrol(patient_id, session_id, self._ctrl._user["id"])
        user = self._ctrl._user
        self._audit.log(user["id"], user["full_name"], "ENROL_PATIENT",
                        f"patient_id:{patient_id}  session_id:{session_id}")
        self.refresh()

    def _open_add(self) -> None:
        from ui.patient_form_dialog import PatientFormDialog
        session    = self._ctrl.get_current_session()
        session_id = session["id"] if session else None
        user = self._ctrl._user
        def _after_save(p: dict) -> None:
            self._audit.log(user["id"], user["full_name"], "ADD_PATIENT",
                            f"HN:{p.get('hn','')}  {p.get('first_name','')} {p.get('last_name','')}")
            self._ctrl.broadcast_refresh()
        PatientFormDialog(
            self,
            user_id=user["id"],
            on_save=_after_save,
            session_id=session_id,
        )

    def _open_edit(self, patient: dict) -> None:
        from ui.patient_form_dialog import PatientFormDialog
        user = self._ctrl._user
        def _after_save(p: dict) -> None:
            self._audit.log(user["id"], user["full_name"], "EDIT_PATIENT",
                            f"HN:{p.get('hn','')}  {p.get('first_name','')} {p.get('last_name','')}")
            self._ctrl.broadcast_refresh()
        PatientFormDialog(
            self,
            user_id=user["id"],
            on_save=_after_save,
            patient=patient,
        )

    def _open_import(self) -> None:
        from ui.import_dialog import ImportDialog
        session    = self._ctrl.get_current_session()
        session_id = session["id"] if session else None
        ImportDialog(
            self,
            user_id=self._ctrl._user["id"],
            session_id=session_id,
            on_complete=lambda _: self.refresh(),
        )
