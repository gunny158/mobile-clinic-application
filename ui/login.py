from __future__ import annotations
from typing import Callable
import customtkinter as ctk
from PIL import Image
from services.auth_service import AuthService
from config import APP_VERSION, LOGO_PATH


class LoginWindow(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, on_success: Callable[[dict], None]) -> None:
        super().__init__(parent)
        self._on_success = on_success
        self._auth = AuthService()

        self.title("BPK1 MOBILE UNIT — เข้าสู่ระบบ")
        self.resizable(False, False)
        self._center(420, 540)
        self._build()

        self.bind("<Return>", lambda _: self._do_login())
        self.after(150, self._entry_username.focus)

        # Prevent closing root when only login window exists
        self.protocol("WM_DELETE_WINDOW", parent.quit)

    # ------------------------------------------------------------------ layout

    def _build(self) -> None:
        self._build_header()
        self._build_form()
        self._build_footer()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="#1a6bb5", corner_radius=0, height=150)
        header.pack(fill="x")
        header.pack_propagate(False)

        try:
            img = Image.open(LOGO_PATH)
            logo_img = ctk.CTkImage(img, size=(220, 53))
            ctk.CTkLabel(header, image=logo_img, text="").pack(pady=(22, 4))
        except Exception:
            ctk.CTkLabel(
                header, text="🏥", font=ctk.CTkFont(size=44, weight="bold")
            ).pack(pady=(22, 2))
            ctk.CTkLabel(
                header, text="BPK1 MOBILE UNIT",
                font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                text_color="white",
            ).pack()
        ctk.CTkLabel(
            header, text="ระบบตรวจสุขภาพเคลื่อนที่",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#cce0f5",
        ).pack()

    def _build_form(self) -> None:
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=44, pady=28)

        # username
        ctk.CTkLabel(
            form, text="ชื่อผู้ใช้งาน", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).pack(fill="x", pady=(0, 4))
        self._entry_username = ctk.CTkEntry(
            form, height=42, placeholder_text="Username",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        )
        self._entry_username.pack(fill="x", pady=(0, 18))

        # password
        ctk.CTkLabel(
            form, text="รหัสผ่าน", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).pack(fill="x", pady=(0, 4))
        self._entry_password = ctk.CTkEntry(
            form, height=42, placeholder_text="Password",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            show="•",
        )
        self._entry_password.pack(fill="x", pady=(0, 24))

        # login button
        self._btn_login = ctk.CTkButton(
            form, text="เข้าสู่ระบบ", height=46,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            fg_color="#1a6bb5", hover_color="#155a9a",
            command=self._do_login,
        )
        self._btn_login.pack(fill="x")

        # error label
        self._lbl_error = ctk.CTkLabel(
            form, text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#e53935",
            wraplength=320,
        )
        self._lbl_error.pack(pady=(10, 0))

    def _build_footer(self) -> None:
        ctk.CTkLabel(
            self,
            text=f"v{APP_VERSION}  |  BPK1 MOBILE UNIT",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="gray",
        ).pack(pady=(0, 14))

    # ------------------------------------------------------------------ logic

    def _do_login(self) -> None:
        username = self._entry_username.get().strip()
        password = self._entry_password.get()

        if not username or not password:
            self._show_error("กรุณากรอกชื่อผู้ใช้งานและรหัสผ่าน")
            return

        self._btn_login.configure(state="disabled", text="กำลังตรวจสอบ…")
        self._lbl_error.configure(text="")
        # Defer so the UI redraws before the blocking bcrypt call
        self.after(80, lambda: self._verify(username, password))

    def _verify(self, username: str, password: str) -> None:
        user = self._auth.login(username, password)
        if user:
            self._on_success(user)
            self.destroy()
        else:
            self._show_error("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
            self._btn_login.configure(state="normal", text="เข้าสู่ระบบ")
            self._entry_password.delete(0, "end")
            self._entry_password.focus()

    def _show_error(self, msg: str) -> None:
        self._lbl_error.configure(text=f"⚠  {msg}")

    # ------------------------------------------------------------------ util

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
