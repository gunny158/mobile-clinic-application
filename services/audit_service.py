from database.connection import get_connection


class AuditService:
    def log(self, user_id: int, user_name: str, action: str, detail: str = "") -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO audit_log (user_id, user_name, action, detail) VALUES (?, ?, ?, ?)",
            (user_id, user_name, action, detail or ""),
        )
        conn.commit()

    def get_recent(self, limit: int = 500) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY performed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
