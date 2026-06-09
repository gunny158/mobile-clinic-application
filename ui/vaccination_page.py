"""Vaccination page — patient list + vaccine entry form + history."""
from __future__ import annotations
import customtkinter as ctk
from services.vaccination_service import (
    VaccinationService, COMMON_VACCINES, ROUTES, SITES, DOSE_OPTIONS
)
from services.queue_service import QueueService, OK, NOT_FOUND, NOT_ENROLLED
from services.audit_service import AuditService
from services.print_service import print_consent_form
from utils.date_utils import be, today_be_long
from config import LOGO_PATH


class VaccinationPage(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color="transparent")
        self._ctrl = controller
        self._svc  = VaccinationService()
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
            bar, text="💉  วัคซีน — Vaccination",
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
            hdr, text="✅=ฉีดแล้ว",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#90a4ae", anchor="e",
        ).pack(side="right", pady=8)

        ctk.CTkFrame(parent, height=1, fg_color="#dde3ec").pack(fill="x", padx=8)

        # ── Barcode scan zone ─────────────────────────────────────────
        scan_zone = ctk.CTkFrame(parent, fg_color="#f3e5f5", corner_radius=0)
        scan_zone.pack(fill="x")

        ctk.CTkLabel(
            scan_zone, text="📷  สแกน HN เพื่อบันทึกวัคซีน",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#6a1b9a",
        ).pack(anchor="w", padx=10, pady=(6, 2))

        scan_row = ctk.CTkFrame(scan_zone, fg_color="transparent")
        scan_row.pack(fill="x", padx=8, pady=(0, 4))

        self._scan_entry = ctk.CTkEntry(
            scan_row,
            placeholder_text="สแกนหรือพิมพ์ HN…",
            height=32,
            font=ctk.CTkFont(family="Courier New", size=14, weight="bold"),
        )
        self._scan_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._scan_entry.bind("<Return>", self._on_scan)

        ctk.CTkButton(
            scan_row, text="→",
            width=32, height=32,
            fg_color="#6a1b9a", hover_color="#4a148c",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            command=self._on_scan,
        ).pack(side="left")

        self._lbl_scan = ctk.CTkLabel(
            scan_zone, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self._lbl_scan.pack(anchor="w", padx=10, pady=(0, 4))

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

        rows = self._svc.get_queue_with_vax_status(session["id"])
        if not rows:
            ctk.CTkLabel(
                self._patient_list_body,
                text="ยังไม่มีผู้ป่วยที่เช็กอินแล้ว",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#b0bec5",
            ).pack(pady=30)
            return

        for i, r in enumerate(rows):
            has_vax  = bool(r["has_vax"])
            done_mark = "✅" if has_vax else "○"
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
                row_frame, text="💉", width=36, height=36,
                fg_color="#f3e5f5", hover_color="#ce93d8",
                text_color="#6a1b9a", font=ctk.CTkFont(size=18, weight="bold"),
                command=lambda rr=r: self._open_patient(rr, session),
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
            text="← คลิก 💉 หรือชื่อผู้ป่วยเพื่อบันทึกวัคซีน",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="#b0bec5",
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _open_patient(self, r: dict, session: dict) -> None:
        for w in self._right.winfo_children():
            w.destroy()
        self._active_patient_id = r["patient_id"]
        VaxEntryPanel(self._right, r, session, self._svc, self._ctrl, on_save=self.refresh)

    # ─── barcode scan ─────────────────────────────────────────────────────

    def _on_scan(self, _event=None) -> None:
        session = self._ctrl.get_current_session()
        if not session:
            self._show_scan_result("⚠  ไม่มี Session ที่เปิดอยู่", "#f57c00")
            return

        identifier = self._scan_entry.get().strip()
        if not identifier:
            return

        result  = QueueService().lookup(identifier, session["id"])
        status  = result["status"]
        patient = result.get("patient")
        name    = f"{patient['first_name']} {patient['last_name']}" if patient else ""

        if status == NOT_FOUND:
            self._show_scan_result(f"❌  ไม่พบ: {identifier}", "#c62828")
        elif status == NOT_ENROLLED:
            self._show_scan_result(f"⚠  {name} ไม่ได้ลงทะเบียนใน Session นี้", "#f57c00")
        else:
            sp = result["sp"]
            if sp["status"] == "pending":
                self._show_scan_result(f"⚠  {name} ยังไม่ได้เช็กอิน", "#f57c00")
            else:
                rows  = self._svc.get_queue_with_vax_status(session["id"])
                match = next((r for r in rows if r["patient_id"] == patient["id"]), None)
                if match:
                    self._open_patient(match, session)
                    self._show_scan_result(
                        f"✅  {name}  คิว #{sp['queue_no']}", "#2e7d32"
                    )
                else:
                    self._show_scan_result(f"⚠  {name} ยังไม่ได้เช็กอิน", "#f57c00")

        self._scan_entry.delete(0, "end")
        self._scan_entry.focus_set()

    def _show_scan_result(self, msg: str, color: str) -> None:
        self._lbl_scan.configure(text=msg, text_color=color)
        self.after(4000, lambda: self._lbl_scan.configure(text=""))


# ─────────────────────────────────────────────────────────────────────────────
# VaxEntryPanel
# ─────────────────────────────────────────────────────────────────────────────

class VaxEntryPanel(ctk.CTkFrame):
    def __init__(self, parent, patient_row: dict, session: dict,
                 svc: VaccinationService, controller, on_save) -> None:
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self._pr      = patient_row
        self._session = session
        self._svc     = svc
        self._ctrl    = controller
        self._on_save = on_save
        self._build()

    def _build(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="#6a1b9a", corner_radius=8, height=50)
        hdr.pack(fill="x", pady=(0, 10))
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text=(f"💉  #{self._pr['queue_no']}  "
                  f"{self._pr['first_name']} {self._pr['last_name']}   "
                  f"HN: {self._pr['hn']}"),
            font=ctk.CTkFont(family="AngsanaUPC", size=19, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=16, pady=10)

        ctk.CTkButton(
            hdr, text="🖨️  พิมพ์แบบฟอร์ม",
            width=160, height=34,
            fg_color="#4a148c", hover_color="#38006b",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._print_consent,
        ).pack(side="right", padx=12)

        tab_row = ctk.CTkFrame(self, fg_color="transparent", height=40)
        tab_row.pack(fill="x")
        tab_row.pack_propagate(False)
        self._tab_btns: dict[str, ctk.CTkButton] = {}

        for key, label in [("entry", "💉  บันทึกวัคซีน"), ("history", "📋  ประวัติวัคซีน")]:
            btn = ctk.CTkButton(
                tab_row, text=label,
                width=200, height=36, corner_radius=6,
                fg_color="#6a1b9a" if key == "entry" else "transparent",
                hover_color="#6a1b9a",
                text_color="white" if key == "entry" else "#37474f",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._tab_btns[key] = btn

        self._tab_content = ctk.CTkFrame(self, fg_color="transparent")
        self._tab_content.pack(fill="both", expand=True, pady=(8, 0))
        self._switch_tab("entry")

    def _print_consent(self) -> None:
        """Generate and print the A5 vaccine consent form for this patient."""
        session_date = ""
        raw = (self._session.get("session_date") or "")[:10]
        if raw:
            try:
                y, m, d = raw.split("-")
                session_date = f"{d}/{m}/{int(y) + 543}"
            except Exception:
                session_date = raw
        if not session_date:
            session_date = today_be_long()

        patient = {
            "hn":         self._pr.get("hn", ""),
            "first_name": self._pr.get("first_name", ""),
            "last_name":  self._pr.get("last_name", ""),
        }
        try:
            print_consent_form(patient, session_date, logo_path=LOGO_PATH)
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showerror("พิมพ์ไม่สำเร็จ", str(exc))

    def _switch_tab(self, key: str) -> None:
        for w in self._tab_content.winfo_children():
            w.destroy()
        for k, btn in self._tab_btns.items():
            btn.configure(
                fg_color="#6a1b9a" if k == key else "transparent",
                text_color="white" if k == key else "#37474f",
            )
        if key == "entry":
            self._build_entry_tab(self._tab_content)
        else:
            self._build_history_tab(self._tab_content)

    # ── Entry tab ─────────────────────────────────────────────────────────

    def _build_entry_tab(self, parent) -> None:
        # ── Given vaccines list ────────────────────────────────────────────
        given_hdr = ctk.CTkFrame(parent, fg_color="#ede7f6", corner_radius=6, height=32)
        given_hdr.pack(fill="x", pady=(0, 4))
        given_hdr.pack_propagate(False)
        ctk.CTkLabel(
            given_hdr, text="✅  วัคซีนที่ฉีดในวันนี้",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#4a148c",
        ).pack(side="left", padx=10, pady=4)

        self._given_container = ctk.CTkScrollableFrame(
            parent, fg_color="transparent", height=160
        )
        self._given_container.pack(fill="x")
        self._refresh_given_list()

        ctk.CTkFrame(parent, height=1, fg_color="#dde3ec").pack(fill="x", pady=(8, 0))

        # ── Add form ───────────────────────────────────────────────────────
        form_hdr = ctk.CTkFrame(parent, fg_color="#f3e5f5", corner_radius=6, height=32)
        form_hdr.pack(fill="x", pady=(8, 4))
        form_hdr.pack_propagate(False)
        ctk.CTkLabel(
            form_hdr, text="➕  เพิ่มรายการวัคซีน",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#6a1b9a",
        ).pack(side="left", padx=10, pady=4)

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def lbl(text: str) -> None:
            ctk.CTkLabel(
                scroll, text=text, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#546e7a",
            ).pack(fill="x", padx=4, pady=(6, 1))

        # ── Quick select ──────────────────────────────────────────────────
        lbl("ชื่อวัคซีน *  (เลือกด่วน หรือพิมพ์เอง)")

        quick_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        quick_frame.pack(fill="x", padx=4, pady=(0, 4))

        self._e_vaccine = ctk.CTkEntry(
            scroll, height=36, placeholder_text="ชื่อวัคซีน *",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        )
        self._e_vaccine.pack(fill="x", padx=4)

        for v in COMMON_VACCINES:
            short = v.split(" ")[0]
            ctk.CTkButton(
                quick_frame, text=short,
                height=28, corner_radius=6,
                fg_color="#ede7f6", hover_color="#ce93d8",
                text_color="#4a148c",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=lambda name=v: self._quick_fill(name),
            ).pack(side="left", padx=(0, 4), pady=2)

        # ── Dose ─────────────────────────────────────────────────────────
        lbl("ครั้งที่ / Dose")
        self._var_dose = ctk.StringVar(value=DOSE_OPTIONS[0])
        ctk.CTkOptionMenu(
            scroll, values=DOSE_OPTIONS, variable=self._var_dose,
            height=36, fg_color="#6a1b9a", button_color="#4a148c",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).pack(fill="x", padx=4, pady=(0, 4))

        # ── Lot number ───────────────────────────────────────────────────
        lbl("Lot Number  (ไม่บังคับ)")
        self._e_lot = ctk.CTkEntry(
            scroll, height=36, placeholder_text="เช่น  AB1234C",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        )
        self._e_lot.pack(fill="x", padx=4)

        # ── Route + Site ─────────────────────────────────────────────────
        rs_row = ctk.CTkFrame(scroll, fg_color="transparent")
        rs_row.pack(fill="x", padx=4, pady=(4, 0))

        route_f = ctk.CTkFrame(rs_row, fg_color="transparent")
        route_f.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(route_f, text="วิธีให้", anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color="#546e7a").pack(fill="x", pady=(0, 2))
        self._var_route = ctk.StringVar(value=ROUTES[0])
        ctk.CTkOptionMenu(
            route_f, values=ROUTES, variable=self._var_route,
            height=36, fg_color="#6a1b9a", button_color="#4a148c",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        ).pack(fill="x")

        site_f = ctk.CTkFrame(rs_row, fg_color="transparent")
        site_f.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(site_f, text="ตำแหน่งฉีด", anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color="#546e7a").pack(fill="x", pady=(0, 2))
        self._var_site = ctk.StringVar(value=SITES[0])
        ctk.CTkOptionMenu(
            site_f, values=SITES, variable=self._var_site,
            height=36, fg_color="#6a1b9a", button_color="#4a148c",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        ).pack(fill="x")

        # ── Notes ─────────────────────────────────────────────────────────
        lbl("หมายเหตุ  (ไม่บังคับ)")
        self._e_notes = ctk.CTkEntry(
            scroll, height=36, placeholder_text="หมายเหตุเพิ่มเติม…",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        )
        self._e_notes.pack(fill="x", padx=4)

        # ── Error + Save ──────────────────────────────────────────────────
        self._lbl_err = ctk.CTkLabel(
            scroll, text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#e53935",
        )
        self._lbl_err.pack(pady=(6, 0))

        ctk.CTkButton(
            scroll,
            text="💾  บันทึกวัคซีน",
            height=44, corner_radius=8,
            fg_color="#6a1b9a", hover_color="#4a148c",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            command=self._submit,
        ).pack(fill="x", padx=4, pady=10)

    def _quick_fill(self, name: str) -> None:
        self._e_vaccine.delete(0, "end")
        self._e_vaccine.insert(0, name)

    def _refresh_given_list(self) -> None:
        for w in self._given_container.winfo_children():
            w.destroy()

        pid = self._pr["patient_id"]
        sid = self._session["id"]
        records = self._svc.get_vaccinations(pid, sid)

        if not records:
            ctk.CTkLabel(
                self._given_container,
                text="ยังไม่มีรายการวัคซีนในวันนี้",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#b0bec5",
            ).pack(anchor="w", padx=10, pady=6)
            return

        for rec in records:
            row = ctk.CTkFrame(self._given_container, fg_color="#ede7f6",
                               corner_radius=6, height=38)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            detail = rec["vaccine_name"]
            if rec.get("dose_no"):
                detail += f"  |  {rec['dose_no']}"
            if rec.get("lot_number"):
                detail += f"  |  Lot: {rec['lot_number']}"
            if rec.get("site"):
                detail += f"  |  {rec['site']}"

            ctk.CTkLabel(
                row, text=detail, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#4a148c",
            ).pack(side="left", padx=(10, 0), fill="x", expand=True)

            ctk.CTkButton(
                row, text="🗑️",
                width=32, height=28,
                fg_color="#ffebee", hover_color="#ef9a9a",
                text_color="#c62828",
                font=ctk.CTkFont(size=15, weight="bold"),
                command=lambda rid=rec["id"]: self._delete_vax(rid),
            ).pack(side="right", padx=8)

    def _delete_vax(self, vax_id: int) -> None:
        from tkinter import messagebox
        if not messagebox.askyesno("ลบรายการ", "ลบรายการวัคซีนนี้?\n\nยืนยัน?"):
            return
        self._svc.delete_vaccination(vax_id)
        user = self._ctrl._user
        name = f"{self._pr['first_name']} {self._pr['last_name']}"
        AuditService().log(user["id"], user["full_name"], "DELETE_VACCINE",
                           f"{name}  HN:{self._pr.get('hn','')}")
        self._refresh_given_list()
        self._on_save()

    def _submit(self) -> None:
        vaccine_name = self._e_vaccine.get().strip()
        if not vaccine_name:
            self._lbl_err.configure(text="⚠  กรุณากรอกชื่อวัคซีน")
            return

        pid = self._pr["patient_id"]
        sid = self._session["id"]
        uid = self._ctrl._user["id"]

        try:
            self._svc.add_vaccination(
                patient_id=pid,
                session_id=sid,
                vaccine_name=vaccine_name,
                dose_no=self._var_dose.get(),
                lot_number=self._e_lot.get(),
                route=self._var_route.get(),
                site=self._var_site.get(),
                notes=self._e_notes.get(),
                user_id=uid,
            )
        except Exception as exc:
            self._lbl_err.configure(text=f"⚠  {exc}")
            return

        # reset form fields
        self._e_vaccine.delete(0, "end")
        self._e_lot.delete(0, "end")
        self._e_notes.delete(0, "end")
        self._var_dose.set(DOSE_OPTIONS[0])
        self._var_route.set(ROUTES[0])
        self._var_site.set(SITES[0])

        user = self._ctrl._user
        name = f"{self._pr['first_name']} {self._pr['last_name']}"
        AuditService().log(user["id"], user["full_name"], "ADD_VACCINE",
                           f"{vaccine_name}  {name}  HN:{self._pr.get('hn','')}")
        self._lbl_err.configure(text="✅  บันทึกสำเร็จ", text_color="#2e7d32")
        self.after(2000, lambda: self._lbl_err.configure(text=""))
        self._refresh_given_list()
        self._on_save()

    # ── History tab ───────────────────────────────────────────────────────

    def _build_history_tab(self, parent) -> None:
        history = self._svc.get_history(self._pr["patient_id"])

        if not history:
            ctk.CTkLabel(
                parent,
                text="ยังไม่มีประวัติการรับวัคซีน",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#b0bec5",
            ).place(relx=0.5, rely=0.5, anchor="center")
            return

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Group by session
        session_groups: dict[int, list[dict]] = {}
        for rec in history:
            sid = rec["session_id"]
            session_groups.setdefault(sid, []).append(rec)

        for sid, records in session_groups.items():
            first    = records[0]
            raw_date = (first["session_date"] or "")[:10]
            try:
                yr_ce    = int(raw_date[:4])
                date_str = f"{raw_date[8:10]}/{raw_date[5:7]}/{be(yr_ce)}"
            except Exception:
                date_str = raw_date

            grp_hdr = ctk.CTkFrame(scroll, fg_color="#ede7f6", corner_radius=6, height=30)
            grp_hdr.pack(fill="x", pady=(8, 2))
            grp_hdr.pack_propagate(False)
            ctk.CTkLabel(
                grp_hdr,
                text=f"📅  {date_str}  —  {first['session_name']}",
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#4a148c",
            ).pack(side="left", padx=10, pady=4)

            for rec in records:
                row = ctk.CTkFrame(scroll, fg_color="white", corner_radius=0, height=30)
                row.pack(fill="x")
                row.pack_propagate(False)

                parts = [rec["vaccine_name"]]
                if rec.get("dose_no"):
                    parts.append(rec["dose_no"])
                if rec.get("lot_number"):
                    parts.append(f"Lot: {rec['lot_number']}")
                if rec.get("route"):
                    parts.append(rec["route"])
                if rec.get("site"):
                    parts.append(rec["site"])

                ctk.CTkLabel(
                    row, text="  •  ".join(parts), anchor="w",
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    text_color="#37474f",
                ).pack(side="left", padx=(12, 0), fill="x", expand=True)

                if rec.get("given_by_name"):
                    ctk.CTkLabel(
                        row, text=rec["given_by_name"], anchor="e",
                        font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                        text_color="#90a4ae",
                    ).pack(side="right", padx=10)

                ctk.CTkFrame(scroll, height=1, fg_color="#f0f0f0").pack(fill="x")
