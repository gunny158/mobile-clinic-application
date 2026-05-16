"""User CRUD — admin-only operations."""
from __future__ import annotations
import bcrypt
from database.connection import get_connection


class UserService:

    def get_all(self) -> list[dict]:
        rows = get_connection().execute(
            "SELECT id, username, full_name, role, is_active, created_at, last_login "
            "FROM users ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, user_id: int) -> dict | None:
        row = get_connection().execute(
            "SELECT id, username, full_name, role, is_active FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def create(self, username: str, full_name: str, role: str, password: str) -> dict:
        conn = get_connection()
        if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            raise ValueError(f"ชื่อผู้ใช้ '{username}' มีอยู่แล้ว")
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (username.strip(), hashed, full_name.strip(), role),
        )
        conn.commit()
        return self.get_by_id(cur.lastrowid)

    def update(self, user_id: int, username: str, full_name: str, role: str) -> None:
        conn = get_connection()
        conflict = conn.execute(
            "SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id)
        ).fetchone()
        if conflict:
            raise ValueError(f"ชื่อผู้ใช้ '{username}' มีอยู่แล้ว")
        conn.execute(
            "UPDATE users SET username = ?, full_name = ?, role = ? WHERE id = ?",
            (username.strip(), full_name.strip(), role, user_id),
        )
        conn.commit()

    def change_password(self, user_id: int, new_password: str) -> None:
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        conn = get_connection()
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user_id))
        conn.commit()

    def toggle_active(self, user_id: int, current_user_id: int) -> None:
        if user_id == current_user_id:
            raise ValueError("ไม่สามารถปิดใช้งานบัญชีของตัวเองได้")
        conn = get_connection()
        conn.execute(
            "UPDATE users SET is_active = NOT is_active WHERE id = ?", (user_id,)
        )
        conn.commit()

    def delete(self, user_id: int, current_user_id: int) -> None:
        if user_id == current_user_id:
            raise ValueError("ไม่สามารถลบบัญชีของตัวเองได้")
        get_connection().execute("DELETE FROM users WHERE id = ?", (user_id,))
        get_connection().commit()
