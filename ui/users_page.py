"""User Management page — create / edit / change password / delete users."""
from __future__ import annotations
import customtkinter as ctk
from services.user_service import UserService
from services.audit_service import AuditService
from utils.date_utils import fmt_datetime_be

_ROLE_LABEL = {"admin": "Admin 🔑", "user": "User"}
_ROLE_COLOR = {"admin": "#c62828", "user": "#1565c0"}


class UsersPage(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color="transparent")
        self._ctrl  = controller
        self._svc   = UserService()
        self._audit = AuditService()
        self._build()
        self.after(200, self.refresh)

    # ─── build ────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_topbar()
        self._build_table()

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=60)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="🔐  จัดการผู้ใช้งาน — User Management",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", padx=20)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=16)

        ctk.CTkButton(
            right, text="➕  เพิ่มผู้ใช้",
            width=130, height=32,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._open_create,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            right, text="📋  ประวัติการใช้งาน",
            width=170, height=32,
            fg_color="#5c6bc0", hover_color="#3949ab",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._open_audit_log,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            right, text="🔄  รีเฟรช",
            width=90, height=32,
            fg_color="#455a64", hover_color="#37474f",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self.refresh,
        ).pack(side="right")

    def _build_table(self) -> None:
        card = ctk.CTkFrame(
            self, fg_color="white", corner_radius=12,
            border_width=1, border_color="#dde3ec",
        )
        card.pack(fill="both", expand=True, padx=20, pady=16)

        COLS = [
            ("ชื่อผู้ใช้",    150),
            ("ชื่อ-นามสกุล",  200),
            ("สิทธิ์",         110),
            ("สถานะ",          100),
            ("เข้าสู่ระบบล่าสุด", 160),
            ("สร้างเมื่อ",     160),
            ("Actions",        260),
        ]
        hdr = ctk.CTkFrame(card, fg_color="#eef2f7", corner_radius=0, height=34)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        for i, (text, width) in enumerate(COLS):
            ctk.CTkLabel(
                hdr, text=text, width=width, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#37474f",
            ).pack(side="left", padx=(14 if i == 0 else 8, 0))

        self._body = ctk.CTkScrollableFrame(card, fg_color="white", corner_radius=0)
        self._body.pack(fill="both", expand=True)

    # ─── data ─────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        for w in self._body.winfo_children():
            w.destroy()

        if self._ctrl._user.get("role") != "admin":
            ctk.CTkLabel(
                self._body,
                text="🔒  เฉพาะ Admin เท่านั้นที่เข้าถึงหน้านี้ได้",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                text_color="#b0bec5",
            ).pack(pady=60)
            return

        users = self._svc.get_all()
        for i, u in enumerate(users):
            bg  = "white" if i % 2 == 0 else "#f7f9fc"
            row = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, height=48)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Username
            ctk.CTkLabel(
                row, text=u["username"], width=150,
                font=ctk.CTkFont(family="Courier New", size=14, weight="bold"),
                text_color="#1a6bb5", anchor="w",
            ).pack(side="left", padx=(14, 0))

            # Full name
            ctk.CTkLabel(
                row, text=u["full_name"], width=200,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#212121", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Role badge
            role   = u.get("role", "user")
            r_col  = _ROLE_COLOR.get(role, "#455a64")
            r_badge = ctk.CTkFrame(row, fg_color=r_col, corner_radius=6, width=90, height=24)
            r_badge.pack(side="left", padx=(8, 0))
            r_badge.pack_propagate(False)
            ctk.CTkLabel(
                r_badge, text=_ROLE_LABEL.get(role, role),
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="white",
            ).place(relx=0.5, rely=0.5, anchor="center")

            # Active badge
            is_active = u.get("is_active", 1)
            a_col  = "#2e7d32" if is_active else "#9e9e9e"
            a_text = "ใช้งาน ✓" if is_active else "ปิด"
            a_badge = ctk.CTkFrame(row, fg_color=a_col, corner_radius=6, width=80, height=24)
            a_badge.pack(side="left", padx=(8, 0))
            a_badge.pack_propagate(False)
            ctk.CTkLabel(
                a_badge, text=a_text,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="white",
            ).place(relx=0.5, rely=0.5, anchor="center")

            # Last login
            last_login = self._fmt_dt(u.get("last_login"))
            ctk.CTkLabel(
                row, text=last_login, width=160,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#78909c", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Created at
            ctk.CTkLabel(
                row, text=self._fmt_dt(u.get("created_at")), width=160,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#78909c", anchor="w",
            ).pack(side="left", padx=(8, 0))

            # Actions
            act = ctk.CTkFrame(row, fg_color="transparent")
            act.pack(side="left", padx=(6, 4))

            ctk.CTkButton(
                act, text="✏️  แก้ไข",
                width=80, height=28,
                fg_color="#1a6bb5", hover_color="#155a9a",
                text_color="white",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=lambda uu=u: self._open_edit(uu),
            ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(
                act, text="🔑  รหัสผ่าน",
                width=100, height=28,
                fg_color="#f57c00", hover_color="#e65100",
                text_color="white",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=lambda uu=u: self._open_password(uu),
            ).pack(side="left", padx=(0, 4))

            me = self._ctrl._user["id"] == u["id"]

            ctk.CTkButton(
                act,
                text="✓ เปิด" if not is_active else "✕ ปิด",
                width=68, height=28,
                fg_color="#455a64" if is_active else "#2e7d32",
                hover_color="#37474f" if is_active else "#1b5e20",
                text_color="white",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                state="disabled" if me else "normal",
                command=lambda uid=u["id"]: self._toggle_active(uid),
            ).pack(side="left", padx=(0, 4))

            ctk.CTkButton(
                act, text="🗑️",
                width=34, height=28,
                fg_color="#e53935", hover_color="#c62828",
                text_color="white",
                font=ctk.CTkFont(size=15, weight="bold"),
                state="disabled" if me else "normal",
                command=lambda uu=u: self._delete(uu),
            ).pack(side="left")

            ctk.CTkFrame(self._body, height=1, fg_color="#f0f0f0").pack(fill="x")

    # ─── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_dt(dt_str) -> str:
        return fmt_datetime_be(dt_str) if dt_str else "—"

    # ─── actions ──────────────────────────────────────────────────────────

    def _open_create(self) -> None:
        actor = self._ctrl._user
        def _after():
            self._audit.log(actor["id"], actor["full_name"], "ADD_USER", "สร้างผู้ใช้ใหม่")
            self.refresh()
        UserFormDialog(self, mode="create", svc=self._svc, on_done=_after)

    def _open_edit(self, user: dict) -> None:
        actor = self._ctrl._user
        def _after():
            self._audit.log(actor["id"], actor["full_name"], "EDIT_USER",
                            f"{user['username']}  ({user['full_name']})")
            self.refresh()
        UserFormDialog(self, mode="edit", svc=self._svc, user=user, on_done=_after)

    def _open_password(self, user: dict) -> None:
        actor = self._ctrl._user
        def _after():
            self._audit.log(actor["id"], actor["full_name"], "CHANGE_PASSWORD",
                            f"{user['username']}")
            self.refresh()
        ChangePasswordDialog(self, svc=self._svc, user=user, on_done=_after)

    def _toggle_active(self, user_id: int) -> None:
        try:
            self._svc.toggle_active(user_id, self._ctrl._user["id"])
            actor = self._ctrl._user
            self._audit.log(actor["id"], actor["full_name"], "TOGGLE_USER",
                            f"user_id:{user_id}")
            self.refresh()
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showerror("Error", str(exc))

    def _delete(self, user: dict) -> None:
        from tkinter import messagebox
        if not messagebox.askyesno(
            "ลบผู้ใช้",
            f"ลบผู้ใช้: {user['username']} ({user['full_name']})\n\nยืนยัน?",
        ):
            return
        try:
            self._svc.delete(user["id"], self._ctrl._user["id"])
            actor = self._ctrl._user
            self._audit.log(actor["id"], actor["full_name"], "DELETE_USER",
                            f"{user['username']}  ({user['full_name']})")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _open_audit_log(self) -> None:
        AuditLogDialog(self, self._audit)


# ══════════════════════════════════════════════════════════════════════════════
# UserFormDialog — create or edit user
# ══════════════════════════════════════════════════════════════════════════════

class UserFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, mode: str, svc: UserService,
                 user: dict | None = None, on_done=None) -> None:
        super().__init__(parent)
        self._mode    = mode
        self._svc     = svc
        self._user    = user
        self._on_done = on_done
        self._role_var = ctk.StringVar(value=(user or {}).get("role", "user"))

        title = "เพิ่มผู้ใช้ใหม่" if mode == "create" else "แก้ไขข้อมูลผู้ใช้"
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self._center(460, mode == "create" and 500 or 440)
        self._build()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self) -> None:
        # Header
        hdr = ctk.CTkFrame(self, fg_color="#1a6bb5", corner_radius=0, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        icon = "➕" if self._mode == "create" else "✏️"
        ctk.CTkLabel(
            hdr,
            text=f"{icon}  {'เพิ่มผู้ใช้ใหม่' if self._mode == 'create' else 'แก้ไขข้อมูลผู้ใช้'}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=12)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=28, pady=16)

        def _field(label: str, placeholder: str, default: str = "") -> ctk.CTkEntry:
            ctk.CTkLabel(form, text=label, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(fill="x", pady=(8, 2))
            e = ctk.CTkEntry(form, placeholder_text=placeholder, height=36,
                             font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
            if default:
                e.insert(0, default)
            e.pack(fill="x")
            return e

        self._e_username  = _field("ชื่อผู้ใช้ (username) *", "เช่น nurse01",
                                   (self._user or {}).get("username", ""))
        self._e_fullname  = _field("ชื่อ-นามสกุล *", "เช่น พยาบาล สมใจ",
                                   (self._user or {}).get("full_name", ""))

        # Role
        ctk.CTkLabel(form, text="สิทธิ์การใช้งาน", anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(fill="x", pady=(8, 2))
        r_row = ctk.CTkFrame(form, fg_color="transparent")
        r_row.pack(fill="x")
        for val, label in [("user", "User (ทั่วไป)"), ("admin", "Admin (ผู้ดูแล)")]:
            ctk.CTkRadioButton(r_row, text=label, value=val, variable=self._role_var,
                               font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="left", padx=(0, 20))

        # Password fields (create mode only)
        if self._mode == "create":
            self._e_pass1 = _field("รหัสผ่าน *", "อย่างน้อย 6 ตัวอักษร")
            self._e_pass1.configure(show="●")
            self._e_pass2 = _field("ยืนยันรหัสผ่าน *", "พิมพ์รหัสผ่านอีกครั้ง")
            self._e_pass2.configure(show="●")

        # Error label
        self._lbl_err = ctk.CTkLabel(self, text="",
                                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                     text_color="#e53935")
        self._lbl_err.pack(pady=(4, 0))

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=28, pady=(6, 20))

        ctk.CTkButton(
            btn_row, text="💾  บันทึก",
            height=42, fg_color="#1a6bb5", hover_color="#155a9a",
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
        username  = self._e_username.get().strip()
        full_name = self._e_fullname.get().strip()
        role      = self._role_var.get()

        if not username:
            self._lbl_err.configure(text="⚠  กรุณากรอกชื่อผู้ใช้")
            return
        if not full_name:
            self._lbl_err.configure(text="⚠  กรุณากรอกชื่อ-นามสกุล")
            return

        try:
            if self._mode == "create":
                p1 = self._e_pass1.get()
                p2 = self._e_pass2.get()
                if len(p1) < 6:
                    self._lbl_err.configure(text="⚠  รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")
                    return
                if p1 != p2:
                    self._lbl_err.configure(text="⚠  รหัสผ่านไม่ตรงกัน")
                    return
                self._svc.create(username, full_name, role, p1)
            else:
                self._svc.update(self._user["id"], username, full_name, role)

            if self._on_done:
                self._on_done()
            self.destroy()
        except Exception as exc:
            self._lbl_err.configure(text=f"⚠  {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# ChangePasswordDialog
# ══════════════════════════════════════════════════════════════════════════════

class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent, svc: UserService, user: dict, on_done=None) -> None:
        super().__init__(parent)
        self._svc     = svc
        self._user    = user
        self._on_done = on_done

        self.title(f"เปลี่ยนรหัสผ่าน — {user['username']}")
        self.resizable(False, False)
        self.grab_set()
        self._center(420, 360)
        self._build()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="#f57c00", corner_radius=0, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr,
            text=f"🔑  เปลี่ยนรหัสผ่าน: {self._user['username']}",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=12)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=28, pady=16)

        def _pw_field(label: str) -> ctk.CTkEntry:
            ctk.CTkLabel(form, text=label, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(fill="x", pady=(8, 2))
            e = ctk.CTkEntry(form, show="●", height=36,
                             font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
            e.pack(fill="x")
            return e

        self._e_new     = _pw_field("รหัสผ่านใหม่ *  (อย่างน้อย 6 ตัวอักษร)")
        self._e_confirm = _pw_field("ยืนยันรหัสผ่านใหม่ *")

        self._lbl_err = ctk.CTkLabel(self, text="",
                                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                     text_color="#e53935")
        self._lbl_err.pack(pady=(4, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=28, pady=(8, 20))

        ctk.CTkButton(
            btn_row, text="🔑  บันทึกรหัสผ่านใหม่",
            height=42, fg_color="#f57c00", hover_color="#e65100",
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
        p1 = self._e_new.get()
        p2 = self._e_confirm.get()
        if len(p1) < 6:
            self._lbl_err.configure(text="⚠  รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")
            return
        if p1 != p2:
            self._lbl_err.configure(text="⚠  รหัสผ่านไม่ตรงกัน")
            return
        try:
            self._svc.change_password(self._user["id"], p1)
            if self._on_done:
                self._on_done()
            self.destroy()
        except Exception as exc:
            self._lbl_err.configure(text=f"⚠  {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# AuditLogDialog — browse action history (admin only)
# ══════════════════════════════════════════════════════════════════════════════

_ACTION_COLOR = {
    "SIGN_IN":          "#2e7d32",
    "SIGN_OUT":         "#5c6bc0",
    "ADD_PATIENT":      "#1565c0",
    "EDIT_PATIENT":     "#f57c00",
    "DELETE_PATIENT":   "#c62828",
    "ENROL_PATIENT":    "#1565c0",
    "CHECK_IN":         "#2e7d32",
    "COMPLETE":         "#1565c0",
    "CHANGE_STATUS":    "#f57c00",
    "SAVE_LAB":         "#1565c0",
    "DELETE_ALL_LAB":   "#c62828",
    "ADD_CUSTOM_LAB":   "#1565c0",
    "DELETE_CUSTOM_LAB":"#c62828",
    "ADD_VACCINE":      "#6a1b9a",
    "DELETE_VACCINE":   "#c62828",
    "ADD_USER":         "#2e7d32",
    "EDIT_USER":        "#f57c00",
    "DELETE_USER":      "#c62828",
    "CHANGE_PASSWORD":  "#f57c00",
    "TOGGLE_USER":      "#455a64",
}


class AuditLogDialog(ctk.CTkToplevel):
    def __init__(self, parent, audit: AuditService) -> None:
        super().__init__(parent)
        self._audit = audit
        self.title("📋  ประวัติการใช้งาน — Audit Log")
        self.grab_set()
        self._center(960, 640)
        self._build()

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self) -> None:
        # Header bar
        hdr = ctk.CTkFrame(self, fg_color="#5c6bc0", corner_radius=0, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr, text="📋  ประวัติการใช้งานระบบ",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=20, pady=12)
        ctk.CTkButton(
            hdr, text="🔄  รีเฟรช",
            width=100, height=32,
            fg_color="#3949ab", hover_color="#283593",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._load,
        ).pack(side="right", padx=16, pady=10)

        # Column headers
        cols = [
            ("วันที่-เวลา",  180),
            ("ผู้ใช้งาน",    160),
            ("Action",       160),
            ("รายละเอียด",   0),    # 0 = fill remaining
        ]
        col_hdr = ctk.CTkFrame(self, fg_color="#eef2f7", corner_radius=0, height=34)
        col_hdr.pack(fill="x")
        col_hdr.pack_propagate(False)
        for i, (text, width) in enumerate(cols):
            kw = {"width": width} if width else {}
            ctk.CTkLabel(
                col_hdr, text=text, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color="#37474f",
                **kw,
            ).pack(side="left", padx=(14 if i == 0 else 8, 0))

        # Scrollable body
        self._body = ctk.CTkScrollableFrame(self, fg_color="white", corner_radius=0)
        self._body.pack(fill="both", expand=True)

        self._load()

    def _load(self) -> None:
        for w in self._body.winfo_children():
            w.destroy()

        rows = self._audit.get_recent(500)
        if not rows:
            ctk.CTkLabel(
                self._body,
                text="ยังไม่มีประวัติการใช้งาน",
                font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color="#b0bec5",
            ).pack(pady=40)
            return

        for i, r in enumerate(rows):
            bg  = "white" if i % 2 == 0 else "#f7f9fc"
            row = ctk.CTkFrame(self._body, fg_color=bg, corner_radius=0, height=36)
            row.pack(fill="x")
            row.pack_propagate(False)

            # Timestamp
            ts = fmt_datetime_be(r.get("performed_at")) if r.get("performed_at") else "—"
            ctk.CTkLabel(
                row, text=ts, width=180, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#546e7a",
            ).pack(side="left", padx=(14, 0))

            # User name
            ctk.CTkLabel(
                row, text=r.get("user_name", "—"), width=160, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#0f2744",
            ).pack(side="left", padx=(8, 0))

            # Action badge
            action     = r.get("action", "")
            act_color  = _ACTION_COLOR.get(action, "#455a64")
            badge = ctk.CTkFrame(row, fg_color=act_color, corner_radius=5, width=150, height=24)
            badge.pack(side="left", padx=(8, 0))
            badge.pack_propagate(False)
            ctk.CTkLabel(
                badge, text=action,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color="white",
            ).place(relx=0.5, rely=0.5, anchor="center")

            # Detail
            ctk.CTkLabel(
                row, text=(r.get("detail") or ""), anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#546e7a",
            ).pack(side="left", padx=(12, 8), fill="x", expand=True)

            ctk.CTkFrame(self._body, height=1, fg_color="#f0f0f0").pack(fill="x")
