from __future__ import annotations
from typing import Callable
import customtkinter as ctk

NAV_ITEMS = [
    ("dashboard",    "🏠", "หน้าหลัก"),
    ("patients",     "👥", "ข้อมูลผู้ป่วย"),
    ("queue",        "📋", "คิวตรวจ"),
    ("sticker",      "🖨", "พิมพ์สติกเกอร์"),
    ("lab",          "🔬", "ผลแล็บ"),
    ("vaccination",  "💉", "วัคซีน"),
    ("export",       "📤", "Export / สำรองข้อมูล"),
    ("users",        "🔐", "จัดการผู้ใช้"),   # admin only — filtered in _build_sidebar
]

_BG      = "#0f2744"   # sidebar background
_ACTIVE  = "#1a6bb5"   # active nav button
_HOVER   = "#1a3a5c"   # hover state
_WIDTH   = 220         # sidebar pixel width


class MainWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTk,
        user: dict,
        on_signout: Callable | None = None,
    ) -> None:
        super().__init__(parent)
        self._user       = user
        self._on_signout = on_signout
        self._session: dict | None = None
        self._nav_btns: dict[str, ctk.CTkButton] = {}
        self._pages: dict[str, ctk.CTkFrame] = {}

        self.title(f"BPK1 MOBILE UNIT  —  {user['full_name']}  [{user['role'].upper()}]")
        self.wm_state("zoomed")
        self.minsize(1024, 640)

        self._build()
        self._navigate("dashboard")

        # Audit: record sign-in
        from services.audit_service import AuditService
        AuditService().log(user["id"], user["full_name"], "SIGN_IN", "")

    # ------------------------------------------------------------------ layout

    def _build(self) -> None:
        sidebar = ctk.CTkFrame(self, width=_WIDTH, fg_color=_BG, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        self._content = ctk.CTkFrame(self, fg_color="#f0f4f8", corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)
        self._build_pages()

    def _build_sidebar(self, sb: ctk.CTkFrame) -> None:
        # ── Logo ──────────────────────────────────────────────────────────
        logo = ctk.CTkFrame(sb, fg_color="transparent", height=88)
        logo.pack(fill="x")
        logo.pack_propagate(False)
        ctk.CTkLabel(
            logo, text="🏥",
            font=ctk.CTkFont(size=33, weight="bold"),
        ).place(relx=0.5, rely=0.32, anchor="center")
        ctk.CTkLabel(
            logo, text="BPK1 MOBILE UNIT",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="white",
        ).place(relx=0.5, rely=0.72, anchor="center")

        ctk.CTkFrame(sb, height=1, fg_color="#1a3a5c").pack(fill="x", padx=14, pady=2)

        # ── Nav buttons ───────────────────────────────────────────────────
        nav_wrap = ctk.CTkFrame(sb, fg_color="transparent")
        nav_wrap.pack(fill="x", padx=10, pady=8)

        is_admin = self._user.get("role") == "admin"
        for key, icon, label in NAV_ITEMS:
            if key == "users" and not is_admin:
                continue
            btn = ctk.CTkButton(
                nav_wrap,
                text=f"  {icon}   {label}",
                anchor="w",
                height=46,
                corner_radius=8,
                fg_color="transparent",
                hover_color=_HOVER,
                text_color="white",
                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", pady=2)
            self._nav_btns[key] = btn

        # ── Sign out button (bottom) ───────────────────────────────────────
        ctk.CTkButton(
            sb,
            text="  🚪   ออกจากระบบ",
            anchor="w",
            height=40,
            corner_radius=8,
            fg_color="#7b1c1c",
            hover_color="#c62828",
            text_color="white",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            command=self._confirm_signout,
        ).pack(fill="x", padx=10, pady=(0, 6), side="bottom")

        # ── User card (bottom) ────────────────────────────────────────────
        ctk.CTkFrame(sb, height=1, fg_color="#1a3a5c").pack(
            fill="x", padx=14, pady=(6, 2), side="bottom"
        )
        card = ctk.CTkFrame(sb, fg_color="#0a1d33", corner_radius=8, height=58)
        card.pack(fill="x", padx=10, pady=(0, 10), side="bottom")
        card.pack_propagate(False)

        ctk.CTkLabel(
            card,
            text=f"👤  {self._user['full_name']}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#aac8e4", anchor="w",
        ).pack(fill="x", padx=10, pady=(10, 2))
        ctk.CTkLabel(
            card,
            text=self._user["role"].upper(),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#4a7a9e", anchor="w",
        ).pack(fill="x", padx=10)

    def _build_pages(self) -> None:
        from ui.dashboard_page    import DashboardPage
        from ui.patients_page     import PatientsPage
        from ui.queue_page        import QueuePage
        from ui.sticker_page      import StickerPage
        from ui.lab_page          import LabPage
        from ui.vaccination_page  import VaccinationPage
        from ui.export_page       import ExportPage
        from ui.users_page        import UsersPage

        self._pages["dashboard"]   = DashboardPage(self._content,   controller=self)
        self._pages["patients"]    = PatientsPage(self._content,     controller=self)
        self._pages["queue"]       = QueuePage(self._content,        controller=self)
        self._pages["sticker"]     = StickerPage(self._content,      controller=self)
        self._pages["lab"]         = LabPage(self._content,          controller=self)
        self._pages["vaccination"] = VaccinationPage(self._content,  controller=self)
        self._pages["export"]      = ExportPage(self._content,       controller=self)
        if self._user.get("role") == "admin":
            self._pages["users"]   = UsersPage(self._content, controller=self)

        for frame in self._pages.values():
            frame.place(x=0, y=0, relwidth=1, relheight=1)
            frame.place_forget()

    # ------------------------------------------------------------------ navigation

    def _navigate(self, key: str) -> None:
        for k, btn in self._nav_btns.items():
            btn.configure(fg_color=_ACTIVE if k == key else "transparent")

        for k, frame in self._pages.items():
            if k == key:
                frame.place(x=0, y=0, relwidth=1, relheight=1)
                if hasattr(frame, "refresh"):
                    frame.refresh()
            else:
                frame.place_forget()

    # ------------------------------------------------------------------ sign out

    def _confirm_signout(self) -> None:
        from tkinter import messagebox
        confirmed = messagebox.askyesno(
            "ออกจากระบบ",
            f"คุณต้องการออกจากระบบหรือไม่?\n\n"
            f"ผู้ใช้: {self._user['full_name']}  [{self._user['role'].upper()}]\n\n"
            f"⚠  กรุณาตรวจสอบว่าบันทึกข้อมูลเรียบร้อยแล้วก่อนออกจากระบบ",
        )
        if not confirmed:
            return
        from services.audit_service import AuditService
        AuditService().log(self._user["id"], self._user["full_name"], "SIGN_OUT", "")
        if self._on_signout:
            self._on_signout()

    # ------------------------------------------------------------------ session API (used by child pages)

    def get_current_session(self) -> dict | None:
        return self._session

    def set_current_session(self, session: dict | None) -> None:
        self._session = session

    def broadcast_refresh(self) -> None:
        """Refresh every page so data stays in sync after any profile edit."""
        for frame in self._pages.values():
            if hasattr(frame, "refresh"):
                try:
                    frame.refresh()
                except Exception:
                    pass
