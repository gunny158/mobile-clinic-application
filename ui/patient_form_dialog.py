"""Add / Edit Patient dialog — Demographics + Medical History tabs."""
from __future__ import annotations
from datetime import date
from typing import Callable
import customtkinter as ctk
from services.patient_service import PatientService
from utils.validators import validate_national_id, normalise_date
from utils.date_utils import fmt_date_be, fmt_datetime_be


def _calc_age(dob_str: str | None) -> str:
    if not dob_str:
        return "—"
    try:
        dob   = date.fromisoformat(str(dob_str)[:10])
        today = date.today()
        age   = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return f"{age} ปี"
    except Exception:
        return "—"

_GENDERS = [("M", "ชาย"), ("F", "หญิง"), ("Other", "อื่นๆ")]


class PatientFormDialog(ctk.CTkToplevel):
    """
    Pass `patient=None` for new patient, or an existing dict to edit.
    `on_save(patient_dict)` is called after a successful save.
    `session_id` — if provided, patient will be enrolled after save.
    """
    def __init__(
        self,
        parent,
        user_id: int,
        on_save: Callable[[dict], None],
        patient: dict | None = None,
        session_id: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._svc        = PatientService()
        self._user_id    = user_id
        self._on_save    = on_save
        self._patient    = patient
        self._session_id = session_id
        self._gender_var = ctk.StringVar(value="M")

        title = "แก้ไขข้อมูลผู้ป่วย" if patient else "เพิ่มผู้ป่วยใหม่"
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        # Extra height for the info strip when editing an existing patient
        self._center(560, 660 if patient else 600)
        self._build()
        if patient:
            self._populate(patient)

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        # Header
        hdr = ctk.CTkFrame(self, fg_color="#1a6bb5", corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr,
            text="👤  " + ("แก้ไขข้อมูลผู้ป่วย" if self._patient else "เพิ่มผู้ป่วยใหม่"),
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=10)

        if self._patient:
            ctk.CTkLabel(
                hdr,
                text=self._patient.get("hn", ""),
                font=ctk.CTkFont(family="Courier New", size=15, weight="bold"),
                text_color="#cce0f5",
            ).pack(side="right", padx=20)

        # ── Info strip (edit mode only) ────────────────────────────────────
        if self._patient:
            p = self._patient
            gender_map = {"M": "ชาย ♂", "F": "หญิง ♀", "Other": "อื่นๆ"}
            gender_str = gender_map.get(p.get("gender") or "", "—")
            age_str    = _calc_age(p.get("date_of_birth"))
            dob_str    = fmt_date_be(p.get("date_of_birth"))
            reg_str    = fmt_datetime_be(p.get("created_at"))

            strip = ctk.CTkFrame(self, fg_color="#eef2f7", corner_radius=0, height=64)
            strip.pack(fill="x")
            strip.pack_propagate(False)

            def _chip(parent, label: str, value: str, value_color: str = "#0f2744"):
                cell = ctk.CTkFrame(parent, fg_color="transparent")
                cell.pack(side="left", padx=16, pady=8)
                ctk.CTkLabel(
                    cell, text=label,
                    font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    text_color="#78909c",
                ).pack(anchor="w")
                ctk.CTkLabel(
                    cell, text=value,
                    font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                    text_color=value_color,
                ).pack(anchor="w")

            _chip(strip, "เพศ",          gender_str,
                  "#1565c0" if p.get("gender") == "M" else "#ad1457" if p.get("gender") == "F" else "#546e7a")
            _chip(strip, "อายุ",          age_str,    "#2e7d32")
            _chip(strip, "วันเกิด",        dob_str,    "#37474f")
            _chip(strip, "ลงทะเบียนเมื่อ", reg_str,    "#546e7a")

        # Tab view
        tabs = ctk.CTkTabview(self, anchor="nw")
        tabs.pack(fill="both", expand=True, padx=16, pady=(10, 0))
        tabs.add("📋  ข้อมูลส่วนตัว")
        tabs.add("🏥  ประวัติสุขภาพ")

        self._build_demographics(tabs.tab("📋  ข้อมูลส่วนตัว"))
        self._build_medical_history(tabs.tab("🏥  ประวัติสุขภาพ"))

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent", height=60)
        footer.pack(fill="x", padx=16, pady=8)
        footer.pack_propagate(False)

        self._lbl_err = ctk.CTkLabel(
            footer, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e53935",
        )
        self._lbl_err.pack(side="left", padx=4)

        save_text = "💾  บันทึก + ลงทะเบียน" if self._session_id else "💾  บันทึก"
        ctk.CTkButton(
            footer, text=save_text,
            width=180, height=40,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._submit,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            footer, text="ยกเลิก",
            width=100, height=40,
            fg_color="#e0e0e0", hover_color="#bdbdbd",
            text_color="#212121",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self.destroy,
        ).pack(side="right")

    def _build_demographics(self, parent) -> None:
        def row_frame():
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", pady=(0, 2))
            return f

        def lbl(text):
            return ctk.CTkLabel(
                row_frame(),
                text=text, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            )

        def entry(placeholder="", width=0):
            kw = {"width": width} if width else {}
            return ctk.CTkEntry(
                parent, placeholder_text=placeholder, height=36,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), **kw,
            )

        lbl("ชื่อ *").pack(fill="x")
        self._e_first = entry("First Name")
        self._e_first.pack(fill="x", pady=(0, 6))

        lbl("นามสกุล *").pack(fill="x")
        self._e_last = entry("Last Name")
        self._e_last.pack(fill="x", pady=(0, 6))

        lbl("เลขบัตรประชาชน (13 หลัก)").pack(fill="x")
        nid_row = ctk.CTkFrame(parent, fg_color="transparent")
        nid_row.pack(fill="x", pady=(0, 6))
        self._e_nid = ctk.CTkEntry(
            nid_row, placeholder_text="0000000000000",
            height=36, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        )
        self._e_nid.pack(side="left", fill="x", expand=True)
        self._lbl_nid_ok = ctk.CTkLabel(
            nid_row, text="", width=30,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self._lbl_nid_ok.pack(side="left", padx=6)
        self._e_nid.bind("<FocusOut>", self._check_nid)

        lbl("วันเกิด (DD/MM/YYYY พ.ศ.)").pack(fill="x")
        self._e_dob = entry("เช่น 15/06/2519 (พ.ศ.)")
        self._e_dob.pack(fill="x", pady=(0, 6))

        lbl("เพศ").pack(fill="x")
        g_row = ctk.CTkFrame(parent, fg_color="transparent")
        g_row.pack(fill="x", pady=(0, 6))
        for val, label in _GENDERS:
            ctk.CTkRadioButton(
                g_row, text=label, value=val, variable=self._gender_var,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            ).pack(side="left", padx=(0, 20))

        lbl("เบอร์โทรศัพท์").pack(fill="x")
        self._e_phone = entry("0812345678")
        self._e_phone.pack(fill="x", pady=(0, 6))

        lbl("แผนก / หน่วยงาน").pack(fill="x")
        self._e_dept = entry("เช่น ฝ่ายบัญชี")
        self._e_dept.pack(fill="x", pady=(0, 6))

    def _build_medical_history(self, parent) -> None:
        def section(label, placeholder, multiline=False):
            ctk.CTkLabel(
                parent, text=label, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            ).pack(fill="x", pady=(8, 2))
            if multiline:
                w = ctk.CTkTextbox(parent, height=56,
                                   font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
            else:
                w = ctk.CTkEntry(parent, height=36, placeholder_text=placeholder,
                                 font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
            w.pack(fill="x")
            return w

        self._e_conditions  = section("โรคประจำตัว",  "เช่น HT, DM, DLP", multiline=True)
        self._e_drug_allerg = section("แพ้ยา",         "เช่น Penicillin")
        self._e_food_allerg = section("แพ้อาหาร",     "เช่น กุ้ง, ถั่ว")
        self._e_medications = section("ยาที่ใช้ประจำ",  "เช่น Metformin 500mg", multiline=True)

        cb_row = ctk.CTkFrame(parent, fg_color="transparent")
        cb_row.pack(fill="x", pady=(12, 0))
        self._chk_smoker  = ctk.CTkCheckBox(cb_row, text="สูบบุหรี่",
                                             font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
        self._chk_smoker.pack(side="left", padx=(0, 24))
        self._chk_drinker = ctk.CTkCheckBox(cb_row, text="ดื่มแอลกอฮอล์",
                                              font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
        self._chk_drinker.pack(side="left")

    # ------------------------------------------------------------------ populate (edit mode)

    def _populate(self, p: dict) -> None:
        def _set(entry, val):
            entry.delete(0, "end")
            if val:
                entry.insert(0, val)

        _set(self._e_first, p.get("first_name"))
        _set(self._e_last,  p.get("last_name"))
        _set(self._e_nid,   p.get("national_id"))
        dob_raw = p.get("date_of_birth")
        _set(self._e_dob, fmt_date_be(dob_raw) if dob_raw else None)
        _set(self._e_phone, p.get("phone"))
        _set(self._e_dept,  p.get("department"))
        self._gender_var.set(p.get("gender") or "M")
        self._check_nid()

        mh = self._svc.get_medical_history(p["id"])
        if mh:
            def _set_tb(tb, val):
                tb.delete("1.0", "end")
                if val:
                    tb.insert("1.0", val)
            _set_tb(self._e_conditions, mh.get("conditions"))
            _set(self._e_drug_allerg, mh.get("drug_allergies"))
            _set(self._e_food_allerg, mh.get("food_allergies"))
            _set_tb(self._e_medications, mh.get("medications"))
            if mh.get("is_smoker"):
                self._chk_smoker.select()
            if mh.get("is_drinker"):
                self._chk_drinker.select()

    # ------------------------------------------------------------------ validation

    def _check_nid(self, _event=None) -> None:
        nid = self._e_nid.get().strip()
        if not nid:
            self._lbl_nid_ok.configure(text="")
            return
        ok = validate_national_id(nid)
        self._lbl_nid_ok.configure(
            text="✅" if ok else "❌",
            text_color="#2e7d32" if ok else "#e53935",
        )

    # ------------------------------------------------------------------ submit

    def _submit(self) -> None:
        first = self._e_first.get().strip()
        last  = self._e_last.get().strip()
        nid   = self._e_nid.get().strip()
        dob   = self._e_dob.get().strip()

        if not first:
            self._lbl_err.configure(text="⚠  กรุณากรอกชื่อ")
            return
        if not last:
            self._lbl_err.configure(text="⚠  กรุณากรอกนามสกุล")
            return
        if nid and not validate_national_id(nid):
            self._lbl_err.configure(text="⚠  เลขบัตรประชาชนไม่ถูกต้อง")
            return

        demo_data = {
            "first_name":   first,
            "last_name":    last,
            "national_id":  nid or None,
            "date_of_birth": normalise_date(dob) if dob else None,
            "gender":       self._gender_var.get(),
            "phone":        self._e_phone.get().strip() or None,
            "department":   self._e_dept.get().strip() or None,
        }

        def _get_tb(tb):
            return tb.get("1.0", "end").strip() or None

        history_data = {
            "conditions":    _get_tb(self._e_conditions),
            "drug_allergies": self._e_drug_allerg.get().strip() or None,
            "food_allergies": self._e_food_allerg.get().strip() or None,
            "medications":   _get_tb(self._e_medications),
            "is_smoker":     self._chk_smoker.get(),
            "is_drinker":    self._chk_drinker.get(),
        }

        try:
            if self._patient:
                self._svc.update(self._patient["id"], demo_data)
                patient = self._svc.get_by_id(self._patient["id"])
            else:
                patient = self._svc.create(demo_data, self._user_id)

            # Always save medical history if any field is filled
            if any(v for v in history_data.values()):
                self._svc.upsert_medical_history(patient["id"], history_data, self._user_id)

            if self._session_id and not self._patient:
                self._svc.enrol(patient["id"], self._session_id, self._user_id)

            self._on_save(patient)
            self.destroy()
        except Exception as exc:
            self._lbl_err.configure(text=f"⚠  {exc}")
