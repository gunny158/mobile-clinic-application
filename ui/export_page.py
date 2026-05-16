"""Export / Backup page."""
from __future__ import annotations
import os
import threading
from pathlib import Path
import customtkinter as ctk
from services.export_service import ExportService
from services.session_service import SessionService


class ExportPage(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color="transparent")
        self._ctrl  = controller
        self._svc   = ExportService()
        self._ssvc  = SessionService()
        self._build()
        self.after(200, self.refresh)

    # ─── build ────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_topbar()

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self._build_session_export(scroll)
        self._build_full_export(scroll)
        self._build_backup(scroll)
        self._build_restore(scroll)
        self._build_file_lists(scroll)

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=60)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(
            bar, text="📤  Export / สำรองข้อมูล",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", padx=20)

    def _card(self, parent, title: str, subtitle: str = "") -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent, fg_color="white", corner_radius=12,
            border_width=1, border_color="#dde3ec",
        )
        card.pack(fill="x", pady=(0, 14))
        hdr = ctk.CTkFrame(card, fg_color="#eef2f7", corner_radius=0, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr, text=title, anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#0f2744",
        ).pack(side="left", padx=14, pady=10)
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=14)
        if subtitle:
            ctk.CTkLabel(
                body, text=subtitle, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#78909c",
            ).pack(fill="x", pady=(0, 8))
        return body

    # ── Section: session export ───────────────────────────────────────────

    def _build_session_export(self, scroll) -> None:
        body = self._card(
            scroll,
            "📋  Export ข้อมูล Session",
            "Export ผู้ป่วย + ผลวัด + ผลแล็บของ Session ที่เลือก เป็นไฟล์ Excel",
        )

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")

        ctk.CTkLabel(
            row, text="เลือก Session:",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        self._session_opts: list[dict] = []
        self._session_menu = ctk.CTkOptionMenu(
            row, width=240, height=34,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            values=["— กรุณารีเฟรช —"],
        )
        self._session_menu.pack(side="left", padx=(0, 10))

        self._lbl_export_sess = ctk.CTkLabel(
            body, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self._lbl_export_sess.pack(anchor="w", pady=(6, 0))

        ctk.CTkButton(
            row, text="📥  Export Session",
            width=150, height=34,
            fg_color="#1a6bb5", hover_color="#155a9a",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._export_session,
        ).pack(side="left")

    def _export_session(self) -> None:
        idx  = self._session_menu.get()
        sopt = next((s for s in self._session_opts if s["label"] == idx), None)
        if not sopt:
            self._lbl_export_sess.configure(text="⚠  กรุณาเลือก Session", text_color="#f57c00")
            return
        self._lbl_export_sess.configure(text="กำลัง export…", text_color="#1a6bb5")

        def _work():
            path = self._svc.export_session_excel(sopt["id"])
            self.after(0, lambda: self._done(self._lbl_export_sess, path))

        threading.Thread(target=_work, daemon=True).start()

    # ── Section: full patient export ──────────────────────────────────────

    def _build_full_export(self, scroll) -> None:
        body = self._card(
            scroll,
            "👥  Export ข้อมูลผู้ป่วยทั้งหมด",
            "Export ข้อมูลผู้ป่วยทั้งหมดพร้อมประวัติสุขภาพ",
        )
        self._lbl_export_all = ctk.CTkLabel(
            body, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self._lbl_export_all.pack(anchor="w", pady=(0, 6))
        ctk.CTkButton(
            body, text="📥  Export ผู้ป่วยทั้งหมด",
            width=200, height=36,
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._export_all,
        ).pack(anchor="w")

    def _export_all(self) -> None:
        self._lbl_export_all.configure(text="กำลัง export…", text_color="#1a6bb5")

        def _work():
            path = self._svc.export_all_patients()
            self.after(0, lambda: self._done(self._lbl_export_all, path))

        threading.Thread(target=_work, daemon=True).start()

    # ── Section: backup ───────────────────────────────────────────────────

    def _build_backup(self, scroll) -> None:
        body = self._card(
            scroll,
            "💾  สำรองข้อมูล (Backup)",
            "สำรองไฟล์ฐานข้อมูล SQLite ไปยัง backups/",
        )
        self._lbl_backup = ctk.CTkLabel(
            body, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self._lbl_backup.pack(anchor="w", pady=(0, 6))
        ctk.CTkButton(
            body, text="💾  Backup ฐานข้อมูล",
            width=180, height=36,
            fg_color="#455a64", hover_color="#37474f",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._backup,
        ).pack(anchor="w")

    def _backup(self) -> None:
        self._lbl_backup.configure(text="กำลัง backup…", text_color="#1a6bb5")

        def _work():
            path = self._svc.backup_database()
            self.after(0, lambda: self._done(self._lbl_backup, path))
            self.after(100, self.refresh)

        threading.Thread(target=_work, daemon=True).start()

    # ── Section: restore ──────────────────────────────────────────────────

    def _build_restore(self, scroll) -> None:
        body = self._card(
            scroll,
            "♻️  กู้คืนข้อมูล (Restore)",
            "⚠  การกู้คืนจะแทนที่ข้อมูลปัจจุบันทั้งหมด  โปรแกรมจะต้องรีสตาร์ทหลังกู้คืน",
        )
        self._lbl_restore = ctk.CTkLabel(
            body, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self._lbl_restore.pack(anchor="w", pady=(0, 6))
        ctk.CTkButton(
            body, text="📂  เลือกไฟล์ Backup เพื่อกู้คืน",
            width=240, height=36,
            fg_color="#c62828", hover_color="#b71c1c",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._restore,
        ).pack(anchor="w")

    def _restore(self) -> None:
        import tkinter.filedialog as fd
        from tkinter import messagebox

        path = fd.askopenfilename(
            title="เลือกไฟล์ Backup",
            filetypes=[("SQLite DB", "*.db"), ("All files", "*.*")],
            initialdir=str(self._svc.list_backups()[0].parent) if self._svc.list_backups() else ".",
        )
        if not path:
            return

        if not messagebox.askyesno(
            "ยืนยันการกู้คืน",
            f"กู้คืนจาก:\n{path}\n\nข้อมูลปัจจุบันจะถูกแทนที่ทั้งหมด\nโปรแกรมจะปิดตัวเองหลังกู้คืน\n\nยืนยัน?",
        ):
            return

        try:
            self._svc.restore_database(path)
            messagebox.showinfo("กู้คืนสำเร็จ", "กู้คืนข้อมูลสำเร็จ\nกรุณาเปิดโปรแกรมใหม่อีกครั้ง")
            self._ctrl.quit() if hasattr(self._ctrl, "quit") else self.master.quit()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    # ── Section: file lists ───────────────────────────────────────────────

    def _build_file_lists(self, scroll) -> None:
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 14))

        # Exports list
        el = ctk.CTkFrame(
            row, fg_color="white", corner_radius=12,
            border_width=1, border_color="#dde3ec",
        )
        el.pack(side="left", fill="both", expand=True, padx=(0, 8))
        ctk.CTkLabel(
            el, text="📄  ไฟล์ Export ล่าสุด", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#0f2744",
        ).pack(fill="x", padx=14, pady=(12, 4))
        self._export_list_frame = ctk.CTkScrollableFrame(el, fg_color="white", height=160)
        self._export_list_frame.pack(fill="x", padx=8, pady=(0, 10))

        # Backups list
        bl = ctk.CTkFrame(
            row, fg_color="white", corner_radius=12,
            border_width=1, border_color="#dde3ec",
        )
        bl.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(
            bl, text="💾  ไฟล์ Backup ล่าสุด", anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#0f2744",
        ).pack(fill="x", padx=14, pady=(12, 4))
        self._backup_list_frame = ctk.CTkScrollableFrame(bl, fg_color="white", height=160)
        self._backup_list_frame.pack(fill="x", padx=8, pady=(0, 10))

    def _render_file_list(self, frame: ctk.CTkScrollableFrame, paths: list[Path]) -> None:
        for w in frame.winfo_children():
            w.destroy()
        if not paths:
            ctk.CTkLabel(frame, text="ยังไม่มีไฟล์",
                         font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                         text_color="#b0bec5").pack(pady=10)
            return
        for p in paths[:20]:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(
                row, text=p.name, anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#37474f",
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="📂",
                width=30, height=24,
                fg_color="transparent", hover_color="#eef2f7",
                text_color="#1a6bb5",
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda pp=p: os.startfile(pp.parent),
            ).pack(side="right")

    # ─── refresh ──────────────────────────────────────────────────────────

    def refresh(self) -> None:
        # Populate session dropdown
        sessions = self._ssvc.get_all_sessions()
        self._session_opts = [
            {"id": s["id"], "label": f"{s['session_code']}  {s['session_date']}"}
            for s in sessions
        ]
        labels = [s["label"] for s in self._session_opts] or ["— ยังไม่มี Session —"]
        self._session_menu.configure(values=labels)
        if labels:
            self._session_menu.set(labels[0])

        self._render_file_list(self._export_list_frame, self._svc.list_exports())
        self._render_file_list(self._backup_list_frame, self._svc.list_backups())

    # ─── helpers ──────────────────────────────────────────────────────────

    def _done(self, lbl: ctk.CTkLabel, path: Path) -> None:
        lbl.configure(text=f"✅  บันทึกที่: {path.name}", text_color="#2e7d32")
        self.refresh()
