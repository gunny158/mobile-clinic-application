import bcrypt
from database.connection import get_connection


class AuthService:
    def login(self, username: str, password: str) -> dict | None:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
        ).fetchone()
        if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
            conn.execute(
                "UPDATE users SET last_login = datetime('now','localtime') WHERE id = ?",
                (row["id"],),
            )
            conn.commit()
            return dict(row)
        return None

    def change_password(self, user_id: int, new_password: str) -> None:
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        conn = get_connection()
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hashed, user_id),
        )
        conn.commit()
