"""Lab results page — patient list + entry form + historical timeline."""
from __future__ import annotations
import customtkinter as ctk
from services.lab_service import LabService, LAB_FIELDS, VITAL_FIELDS, RANGES
from services.queue_service import QueueService, OK, NOT_FOUND, NOT_ENROLLED
from services.audit_service import AuditService
from utils.date_utils import be

# Map field key → which DB table it lives in
_FIELD_TABLE: dict[str, str] = {
    **{k: "vitals"      for k, _ in VITAL_FIELDS},
    **{k: "lab_results" for k, _ in LAB_FIELDS},
}


class LabPage(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color="transparent")
        self._ctrl              = controller
        self._svc               = LabService()
        self._audit             = AuditService()
        self._active_patient_id: int | None = None
        self._build()
        self.after(200, self.refresh)

    # ─── build ────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_topbar()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        left = ctk.CTkFrame(body, fg_color="white", corner_radius=12,
                            border_width=1, border_color="#dde3ec", width=360)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)
        self._build_patient_list(left)

        self._right = ctk.CTkFrame(body, fg_color="transparent")
        self._right.pack(side="left", fill="both", expand=True)
        self._show_placeholder()

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(
            bar, text="🔬  ผลแล็บ — Lab Results",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            bar, text="🔄  รีเฟรช",
            width=100, height=34,
            fg_color="#455a64", hover_color="#37474f",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self.refresh,
        ).pack(side="right", padx=16)

    def _build_patient_list(self, parent) -> None:
        hdr = ctk.CTkFrame(parent, fg_color="transparent", height=44)
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text="ผู้ป่วยที่เช็กอินแล้ว",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#0f2744", anchor="w",
        ).pack(side="left", pady=8)

        ctk.CTkLabel(
            hdr, text="📝=บันทึก  🗑=ลบ",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#90a4ae", anchor="e",
        ).pack(side="right", pady=8)

        ctk.CTkFrame(parent, height=1, fg_color="#dde3ec").pack(fill="x", padx=8)

        # ── Barcode scan zone ─────────────────────────────────────────
        scan_zone = ctk.CTkFrame(parent, fg_color="#e8f4fd", corner_radius=0)
        scan_zone.pack(fill="x")

        ctk.CTkLabel(
            scan_zone, text="📷  สแกน HN เพื่อเปิดผลแล็บ",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#1a6bb5",
        ).pack(anchor="w", padx=10, pady=(6, 2))

        scan_row = ctk.CTkFrame(scan_zone, fg_color="transparent")
        scan_row.pack(fill="x", padx=8, pady=(0, 4))

        self._lab_scan_entry = ctk.CTkEntry(
            scan_row,
            placeholder_text="สแกนหรือพิมพ์ HN…",
            height=32,
            font=ctk.CTkFont(family="Courier New", size=14, weight="bold"),
        )
        self._lab_scan_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._lab_scan_entry.bind("<Return>", self._on_lab_scan)

        ctk.CTkButton(
            scan_row, text="→",
            width=32, height=32,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            command=self._on_lab_scan,
        ).pack(side="left")

        self._lbl_lab_scan = ctk.CTkLabel(
            scan_zone, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self._lbl_lab_scan.pack(anchor="w", padx=10, pady=(0, 4))

        ctk.CTkFrame(parent, height=1, fg_color="#dde3ec").pack(fill="x", padx=8)

        self._patient_list_body = ctk.CTkScrollableFrame(
            parent, fg_color="white", corner_radius=0
        )
        self._patient_list_body.pack(fill="both", expand=True)

    # ─── data ─────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        session = self._ctrl.get_current_session()
        for w in self._patient_list_body.winfo_children():
            w.destroy()

        if not session:
            ctk.CTkLabel(
                self._patient_list_body,
                text="ยังไม่มี Session ที่เปิดอยู่",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#b0bec5",
            ).pack(pady=30)
            return

        rows = self._svc.get_queue_with_lab_status(session["id"])
        if not rows:
            ctk.CTkLabel(
                self._patient_list_body,
                text="ยังไม่มีผู้ป่วยที่เช็กอินแล้ว",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#b0bec5",
            ).pack(pady=30)
            return

        for i, r in enumerate(rows):
            has_data  = bool(r["has_vitals"] or r["has_labs"])
            done_mark = "✅" if has_data else "○"
            bg        = "white" if i % 2 == 0 else "#f7f9fc"

            row_frame = ctk.CTkFrame(
                self._patient_list_body, fg_color=bg, corner_radius=0, height=46
            )
            row_frame.pack(fill="x")
            row_frame.pack_propagate(False)

            ctk.CTkButton(
                row_frame,
                text=f" {done_mark} #{r['queue_no']}  {r['first_name']} {r['last_name']}",
                anchor="w", height=44, corner_radius=0,
                fg_color="transparent", hover_color="#eef2f7",
                text_color="#212121",
                font=ctk.CTkFont(family="AngsanaUPC", size=18, weight="bold"),
                command=lambda rr=r: self._open_patient(rr, session),
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkButton(
                row_frame, text="📝", width=36, height=36,
                fg_color="#e3f2fd", hover_color="#90caf9",
                text_color="#1565c0", font=ctk.CTkFont(size=18, weight="bold"),
                command=lambda rr=r: self._open_patient(rr, session),
            ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(
                row_frame, text="🗑️", width=36, height=36,
                fg_color="#ffebee" if has_data else "#f5f5f5",
                hover_color="#ef9a9a" if has_data else "#f5f5f5",
                text_color="#c62828" if has_data else "#bdbdbd",
                font=ctk.CTkFont(size=17, weight="bold"),
                state="normal" if has_data else "disabled",
                command=lambda rr=r, s=session: self._confirm_delete_all(rr, s),
            ).pack(side="left", padx=(0, 8))

            ctk.CTkFrame(
                self._patient_list_body, height=1, fg_color="#f0f0f0"
            ).pack(fill="x")

    # ─── right panel ──────────────────────────────────────────────────────

    def _show_placeholder(self) -> None:
        for w in self._right.winfo_children():
            w.destroy()
        self._active_patient_id = None
        ctk.CTkLabel(
            self._right,
            text="← คลิก 📝 หรือชื่อผู้ป่วยเพื่อบันทึกผลแล็บ",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#b0bec5",
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _open_patient(self, r: dict, session: dict) -> None:
        for w in self._right.winfo_children():
            w.destroy()
        self._active_patient_id = r["patient_id"]
        LabEntryPanel(self._right, r, session, self._svc, self._ctrl, on_save=self.refresh)

    def _confirm_delete_all(self, r: dict, session: dict) -> None:
        from tkinter import messagebox
        name = f"{r['first_name']} {r['last_name']}"
        if not messagebox.askyesno(
            "ลบข้อมูลแล็บ",
            f"ลบข้อมูลผลแล็บและสัญญาณชีพทั้งหมดของ:\n{name}  (คิว #{r['queue_no']})\nใน Session นี้\n\nยืนยัน?",
        ):
            return
        self._svc.delete_session_data(r["patient_id"], session["id"])
        user = self._ctrl._user
        self._audit.log(user["id"], user["full_name"], "DELETE_ALL_LAB",
                        f"{name}  HN:{r.get('hn','')}  คิว#{r['queue_no']}")
        if self._active_patient_id == r["patient_id"]:
            self._show_placeholder()
        self.refresh()

    # ─── barcode scan → open patient ──────────────────────────────────────

    def _on_lab_scan(self, _event=None) -> None:
        session = self._ctrl.get_current_session()
        if not session:
            self._show_lab_scan_result("⚠  ไม่มี Session ที่เปิดอยู่", "#f57c00")
            return

        identifier = self._lab_scan_entry.get().strip()
        if not identifier:
            return

        result  = QueueService().lookup(identifier, session["id"])
        status  = result["status"]
        patient = result.get("patient")
        name    = f"{patient['first_name']} {patient['last_name']}" if patient else ""

        if status == NOT_FOUND:
            self._show_lab_scan_result(f"❌  ไม่พบ: {identifier}", "#c62828")
        elif status == NOT_ENROLLED:
            self._show_lab_scan_result(f"⚠  {name} ไม่ได้ลงทะเบียนใน Session นี้", "#f57c00")
        else:
            sp = result["sp"]
            if sp["status"] == "pending":
                self._show_lab_scan_result(f"⚠  {name} ยังไม่ได้เช็กอิน", "#f57c00")
            else:
                rows  = self._svc.get_queue_with_lab_status(session["id"])
                match = next((r for r in rows if r["patient_id"] == patient["id"]), None)
                if match:
                    self._open_patient(match, session)
                    self._show_lab_scan_result(
                        f"✅  {name}  คิว #{sp['queue_no']}", "#2e7d32"
                    )
                else:
                    self._show_lab_scan_result(f"⚠  {name} ยังไม่ได้เช็กอิน", "#f57c00")

        self._lab_scan_entry.delete(0, "end")
        self._lab_scan_entry.focus_set()

    def _show_lab_scan_result(self, msg: str, color: str) -> None:
        self._lbl_lab_scan.configure(text=msg, text_color=color)
        self.after(4000, lambda: self._lbl_lab_scan.configure(text=""))

    def refresh_if_session(self) -> None:
        self.refresh()


# ─────────────────────────────────────────────────────────────────────────────
# LabEntryPanel
# ─────────────────────────────────────────────────────────────────────────────

class LabEntryPanel(ctk.CTkFrame):
    def __init__(self, parent, patient_row: dict, session: dict,
                 svc: LabService, controller, on_save) -> None:
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self._pr      = patient_row
        self._session = session
        self._svc     = svc
        self._ctrl    = controller
        self._on_save = on_save
        self._build()

    def _build(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="#1a6bb5", corner_radius=8, height=50)
        hdr.pack(fill="x", pady=(0, 10))
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text=(f"👤  #{self._pr['queue_no']}  "
                  f"{self._pr['first_name']} {self._pr['last_name']}   "
                  f"HN: {self._pr['hn']}"),
            font=ctk.CTkFont(family="AngsanaUPC", size=19, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=16, pady=10)

        tab_row = ctk.CTkFrame(self, fg_color="transparent", height=40)
        tab_row.pack(fill="x")
        tab_row.pack_propagate(False)
        self._tab_btns: dict[str, ctk.CTkButton] = {}

        for key, label in [("entry", "📝  บันทึกผล"), ("timeline", "📊  ประวัติย้อนหลัง")]:
            btn = ctk.CTkButton(
                tab_row, text=label,
                width=190, height=36, corner_radius=6,
                fg_color="#1a6bb5" if key == "entry" else "transparent",
                hover_color="#1a6bb5",
                text_color="white" if key == "entry" else "#37474f",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._tab_btns[key] = btn

        self._tab_content = ctk.CTkFrame(self, fg_color="transparent")
        self._tab_content.pack(fill="both", expand=True, pady=(8, 0))
        self._switch_tab("entry")

    def _switch_tab(self, key: str) -> None:
        for w in self._tab_content.winfo_children():
            w.destroy()
        for k, btn in self._tab_btns.items():
            btn.configure(
                fg_color="#1a6bb5" if k == key else "transparent",
                text_color="white" if k == key else "#37474f",
            )
        if key == "entry":
            self._build_entry_tab(self._tab_content)
        else:
            self._build_timeline_tab(self._tab_content)

    # ── Entry tab ─────────────────────────────────────────────────────────

    def _build_entry_tab(self, parent) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        pid = self._pr["patient_id"]
        sid = self._session["id"]
        existing_vitals = self._svc.get_vitals(pid, sid)
        existing_labs   = self._svc.get_labs(pid, sid)

        if existing_vitals or existing_labs:
            ctk.CTkLabel(
                scroll,
                text="✅  มีข้อมูลบันทึกแล้ว — แก้ไขและกด บันทึก เพื่ออัปเดต",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#2e7d32",
            ).pack(anchor="w", padx=4, pady=(4, 2))

        # ── section header helper ──────────────────────────────────────────
        def section_header(text: str) -> None:
            f = ctk.CTkFrame(scroll, fg_color="#eef2f7", corner_radius=6, height=32)
            f.pack(fill="x", pady=(10, 4))
            f.pack_propagate(False)
            ctk.CTkLabel(
                f, text=text, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#37474f",
            ).pack(side="left", padx=10, pady=4)

        # ── field row with 🗑️ delete icon ────────────────────────────────
        def field_row(
            label: str, key: str, existing: dict, table: str,
        ) -> ctk.CTkEntry:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=label, width=190, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            ).pack(side="left")

            entry = ctk.CTkEntry(
                row, width=130, height=34,
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                placeholder_text="—",
            )
            entry.pack(side="left", padx=(0, 6))

            val = existing.get(key)
            if val is not None:
                entry.insert(0, str(val))

            # 🗑️ clears the entry widget + NULLs the value in DB immediately
            def _clear(e=entry, k=key, t=table):
                e.delete(0, "end")
                if existing.get(k) is not None:
                    try:
                        self._svc.clear_template_field(pid, sid, k, t)
                        self._on_save()
                    except Exception:
                        pass

            has_val = val is not None
            ctk.CTkButton(
                row, text="🗑️",
                width=30, height=30,
                fg_color="#ffebee" if has_val else "#f5f5f5",
                hover_color="#ef9a9a" if has_val else "#f5f5f5",
                text_color="#c62828" if has_val else "#bdbdbd",
                font=ctk.CTkFont(size=15, weight="bold"),
                command=_clear,
            ).pack(side="left")

            return entry

        # ── Vitals ────────────────────────────────────────────────────────
        section_header("🩺  สัญญาณชีพ & ร่างกาย")
        self._vital_entries: dict[str, ctk.CTkEntry] = {}
        for key, label in VITAL_FIELDS:
            self._vital_entries[key] = field_row(label, key, existing_vitals, "vitals")

        ctk.CTkLabel(
            scroll, text="💡 BMI คำนวณอัตโนมัติจาก น้ำหนัก/ส่วนสูง",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#78909c",
        ).pack(anchor="w", padx=4, pady=(0, 4))

        # ── Template lab fields ───────────────────────────────────────────
        section_header("🧪  ผลตรวจเลือด (Template)")
        self._lab_entries: dict[str, ctk.CTkEntry] = {}
        for key, label in LAB_FIELDS:
            self._lab_entries[key] = field_row(label, key, existing_labs, "lab_results")

        # ── Custom lab results section ────────────────────────────────────
        custom_hdr = ctk.CTkFrame(scroll, fg_color="#fff8e1", corner_radius=6, height=36)
        custom_hdr.pack(fill="x", pady=(10, 4))
        custom_hdr.pack_propagate(False)

        ctk.CTkLabel(
            custom_hdr, text="➕  ผลแล็บเพิ่มเติม (Custom)",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#e65100",
        ).pack(side="left", padx=10, pady=4)

        ctk.CTkButton(
            custom_hdr, text="➕ เพิ่มรายการ",
            width=130, height=28,
            fg_color="#ff8f00", hover_color="#e65100",
            text_color="white",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=lambda: self._open_add_custom_dialog(scroll),
        ).pack(side="right", padx=8, pady=4)

        self._custom_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self._custom_container.pack(fill="x")
        self._refresh_custom_rows()

        # ── Error label + Save button ─────────────────────────────────────
        self._lbl_err = ctk.CTkLabel(
            scroll, text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#e53935",
        )
        self._lbl_err.pack(pady=(8, 0))

        ctk.CTkButton(
            scroll,
            text="💾  บันทึกผลแล็บ",
            height=44, corner_radius=8,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            command=self._submit,
        ).pack(fill="x", padx=4, pady=10)

    # ── Custom lab rows ───────────────────────────────────────────────────

    def _refresh_custom_rows(self) -> None:
        for w in self._custom_container.winfo_children():
            w.destroy()

        pid = self._pr["patient_id"]
        sid = self._session["id"]
        customs = self._svc.get_custom_labs(pid, sid)

        if not customs:
            ctk.CTkLabel(
                self._custom_container,
                text="ยังไม่มีรายการเพิ่มเติม  •  กด ➕ เพิ่มรายการ",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#b0bec5",
            ).pack(anchor="w", padx=10, pady=6)
            return

        for c in customs:
            row = ctk.CTkFrame(self._custom_container, fg_color="#fffde7",
                               corner_radius=6, height=36)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            ctk.CTkLabel(
                row,
                text=c["test_name"],
                width=200, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#e65100",
            ).pack(side="left", padx=(10, 0))

            val_unit = c["value"] or "—"
            if c.get("unit"):
                val_unit += f"  {c['unit']}"
            ctk.CTkLabel(
                row, text=val_unit, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#37474f",
            ).pack(side="left", padx=(8, 0), fill="x", expand=True)

            ctk.CTkButton(
                row, text="🗑️",
                width=32, height=28,
                fg_color="#ffebee", hover_color="#ef9a9a",
                text_color="#c62828",
                font=ctk.CTkFont(size=15, weight="bold"),
                command=lambda cid=c["id"]: self._delete_custom(cid),
            ).pack(side="right", padx=8)

    def _delete_custom(self, custom_id: int) -> None:
        from tkinter import messagebox
        if not messagebox.askyesno("ลบรายการ", "ลบรายการผลแล็บเพิ่มเติมนี้?\n\nยืนยัน?"):
            return
        self._svc.delete_custom_lab(custom_id)
        user = self._ctrl._user
        name = f"{self._pr['first_name']} {self._pr['last_name']}"
        AuditService().log(user["id"], user["full_name"], "DELETE_CUSTOM_LAB",
                           f"{name}  HN:{self._pr.get('hn','')}")
        self._refresh_custom_rows()
        self._on_save()

    def _open_add_custom_dialog(self, scroll) -> None:
        AddCustomLabDialog(
            self,
            patient_id=self._pr["patient_id"],
            session_id=self._session["id"],
            user_id=self._ctrl._user["id"],
            svc=self._svc,
            on_done=lambda: (self._refresh_custom_rows(), self._on_save()),
        )

    # ── Submit ────────────────────────────────────────────────────────────

    def _submit(self) -> None:
        def _parse(entries: dict[str, ctk.CTkEntry]) -> dict[str, float | None]:
            out = {}
            for key, entry in entries.items():
                raw = entry.get().strip()
                if not raw:
                    out[key] = None
                    continue
                try:
                    out[key] = float(raw)
                except ValueError:
                    self._lbl_err.configure(text=f"⚠  ค่า '{key}' ต้องเป็นตัวเลข")
                    raise
            return out

        try:
            vitals = _parse(self._vital_entries)
            labs   = _parse(self._lab_entries)
        except ValueError:
            return

        w = vitals.get("weight_kg")
        h = vitals.get("height_cm")
        if w and h and h > 0 and not vitals.get("bmi"):
            vitals["bmi"] = round(w / ((h / 100) ** 2), 1)

        vitals_clean = {k: v for k, v in vitals.items() if v is not None}
        labs_clean   = {k: v for k, v in labs.items()   if v is not None}

        uid = self._ctrl._user["id"]
        pid = self._pr["patient_id"]
        sid = self._session["id"]

        if vitals_clean:
            self._svc.save_vitals(pid, sid, vitals_clean, uid)
        if labs_clean:
            self._svc.save_labs(pid, sid, labs_clean, uid)

        user = self._ctrl._user
        name = f"{self._pr['first_name']} {self._pr['last_name']}"
        AuditService().log(user["id"], user["full_name"], "SAVE_LAB",
                           f"{name}  HN:{self._pr.get('hn','')}  คิว#{self._pr['queue_no']}")
        self._lbl_err.configure(text="✅  บันทึกสำเร็จ", text_color="#2e7d32")
        self._on_save()

    # ── Timeline tab ──────────────────────────────────────────────────────

    def _build_timeline_tab(self, parent) -> None:
        timeline = self._svc.get_timeline(self._pr["patient_id"], years=3)

        if not timeline:
            ctk.CTkLabel(
                parent,
                text="ยังไม่มีข้อมูลประวัติ",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#b0bec5",
            ).place(relx=0.5, rely=0.5, anchor="center")
            return

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        hdr = ctk.CTkFrame(scroll, fg_color="#eef2f7", corner_radius=6, height=36)
        hdr.pack(fill="x", pady=(0, 4))
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="รายการ", width=160, anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color="#37474f").pack(side="left", padx=(10, 0))

        for t in timeline:
            raw_date = (t["session_date"] or "")[:10]
            try:
                yr_ce    = int(raw_date[:4])
                date_str = f"{raw_date[5:]}/{be(yr_ce)}"
            except Exception:
                date_str = raw_date
            ctk.CTkLabel(hdr, text=date_str, width=120, anchor="center",
                         font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                         text_color="#1a6bb5").pack(side="left", padx=4)

        def render_group(group_label: str, fields, data_key: str) -> None:
            g = ctk.CTkFrame(scroll, fg_color="#f5f7fa", corner_radius=0, height=28)
            g.pack(fill="x", pady=(6, 0))
            g.pack_propagate(False)
            ctk.CTkLabel(g, text=group_label, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                         text_color="#546e7a").pack(side="left", padx=10)

            for field_key, field_label in fields:
                row = ctk.CTkFrame(scroll, fg_color="white", corner_radius=0, height=30)
                row.pack(fill="x")
                row.pack_propagate(False)

                ctk.CTkLabel(row, text=field_label, width=160, anchor="w",
                             font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                             text_color="#37474f").pack(side="left", padx=(10, 0))

                for t in timeline:
                    val     = t[data_key].get(field_key)
                    val_str = f"{val:.1f}" if val is not None else "—"
                    lo, hi  = RANGES.get(field_key, (None, None))
                    color   = "#212121"
                    if val is not None:
                        if (lo is not None and val < lo) or (hi is not None and val > hi):
                            color = "#c62828"
                    ctk.CTkLabel(row, text=val_str, width=120, anchor="center",
                                 font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                 text_color=color).pack(side="left", padx=4)

                ctk.CTkFrame(scroll, height=1, fg_color="#f0f0f0").pack(fill="x")

        render_group("🩺  สัญญาณชีพ & ร่างกาย", VITAL_FIELDS, "vitals")
        render_group("🧪  ผลตรวจเลือด",          LAB_FIELDS,   "labs")


# ─────────────────────────────────────────────────────────────────────────────
# AddCustomLabDialog  — pop-up to enter one custom lab row
# ─────────────────────────────────────────────────────────────────────────────

class AddCustomLabDialog(ctk.CTkToplevel):
    def __init__(self, parent, patient_id: int, session_id: int,
                 user_id: int, svc: LabService, on_done) -> None:
        super().__init__(parent)
        self._pid     = patient_id
        self._sid     = session_id
        self._uid     = user_id
        self._svc     = svc
        self._on_done = on_done

        self.title("➕  เพิ่มผลแล็บเพิ่มเติม")
        self.resizable(False, False)
        self.grab_set()
        self._center(420, 320)
        self._build()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="#ff8f00", corner_radius=0, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr, text="➕  เพิ่มผลแล็บเพิ่มเติม",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=12)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=28, pady=20)

        def _lbl(text: str) -> None:
            ctk.CTkLabel(form, text=text, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
                         ).pack(fill="x", pady=(8, 2))

        def _entry(placeholder: str) -> ctk.CTkEntry:
            e = ctk.CTkEntry(form, height=38, placeholder_text=placeholder,
                             font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"))
            e.pack(fill="x")
            return e

        _lbl("ชื่อการตรวจ *  (เช่น  CA-125, CEA, AFP)")
        self._e_name  = _entry("ชื่อรายการตรวจ")

        _lbl("ค่าที่ได้  *")
        self._e_value = _entry("เช่น  12.5")

        _lbl("หน่วย  (ไม่บังคับ)")
        self._e_unit  = _entry("เช่น  U/mL, ng/mL")

        self._lbl_err = ctk.CTkLabel(self, text="",
                                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                     text_color="#e53935")
        self._lbl_err.pack(pady=(0, 4))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=28, pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="💾  บันทึก",
            height=42, fg_color="#ff8f00", hover_color="#e65100",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._submit,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="ยกเลิก",
            height=42, width=100, fg_color="#e0e0e0", hover_color="#bdbdbd",
            text_color="#212121", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self.destroy,
        ).pack(side="left")

    def _submit(self) -> None:
        name  = self._e_name.get().strip()
        value = self._e_value.get().strip()
        unit  = self._e_unit.get().strip()

        if not name:
            self._lbl_err.configure(text="⚠  กรุณากรอกชื่อการตรวจ")
            return
        if not value:
            self._lbl_err.configure(text="⚠  กรุณากรอกค่าที่ได้")
            return

        try:
            self._svc.save_custom_lab(self._pid, self._sid, name, value, unit, self._uid)
            self._on_done()
            self.destroy()
        except Exception as exc:
            self._lbl_err.configure(text=f"⚠  {exc}")
