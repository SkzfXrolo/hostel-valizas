"""WhatsApp reminders: 48h pre-arrival nudge + post-checkout review ask.

Nothing here sends messages automatically — `due_reminders`/`due_reviews`
only compute *who* is due, and the Operador tab ("Enviar recordatorios
pendientes") is the one place that actually sends, one click at a time, so
Leo/Rubén stay in control (see mejoras-manana.txt #73/#74).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from . import db

REMINDER_DAYS_BEFORE = 2  # "48h antes" ~ 2 días de anticipación


def _reservations_for_check_in(day: date) -> list[dict[str, Any]]:
    d = day.isoformat()
    with db.db() as conn:
        rows = conn.execute(
            """
            SELECT r.*, rm.name AS room_name FROM reservations r
            JOIN rooms rm ON rm.id = r.room_id
            WHERE r.status = 'confirmed' AND r.check_in = ?
            ORDER BY r.guest_name
            """,
            (d,),
        ).fetchall()
        return [dict(row) for row in rows]


def _reservations_for_check_out(day: date) -> list[dict[str, Any]]:
    d = day.isoformat()
    with db.db() as conn:
        rows = conn.execute(
            """
            SELECT r.*, rm.name AS room_name FROM reservations r
            JOIN rooms rm ON rm.id = r.room_id
            WHERE r.status IN ('confirmed', 'checked_out') AND r.check_out = ?
            ORDER BY r.guest_name
            """,
            (d,),
        ).fetchall()
        return [dict(row) for row in rows]


def due_reminders(today: date | None = None) -> list[dict[str, Any]]:
    """Confirmed reservations checking in in `REMINDER_DAYS_BEFORE` days, not yet reminded."""
    today = today or date.today()
    target = today + timedelta(days=REMINDER_DAYS_BEFORE)
    return [r for r in _reservations_for_check_in(target) if not r.get("reminded_at")]


def due_reviews(today: date | None = None) -> list[dict[str, Any]]:
    """Reservations that checked out yesterday and haven't been asked for a review yet."""
    today = today or date.today()
    yesterday = today - timedelta(days=1)
    return [r for r in _reservations_for_check_out(yesterday) if not r.get("reviewed_at")]


def mark_reminded(res_id: int) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with db.db() as conn:
        conn.execute("UPDATE reservations SET reminded_at = ? WHERE id = ?", (now, res_id))


def mark_reviewed(res_id: int) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with db.db() as conn:
        conn.execute("UPDATE reservations SET reviewed_at = ? WHERE id = ?", (now, res_id))


def draft_reminder_message(res: dict[str, Any]) -> str:
    """Short 48h-before-arrival WhatsApp nudge."""
    name = (res.get("guest_name") or "").split(" ")[0] or ""
    hello = f"¡Hola {name}!" if name else "¡Hola!"
    room = res.get("room_name") or res.get("room_id") or "tu habitación"
    check_in = res.get("check_in") or ""
    return (
        f"{hello} Te escribimos de Valizas Hostel: en 2 días te esperamos "
        f"({check_in}) en {room}. Check-in desde las 14:00. "
        "Cualquier cosa, avisanos por acá. ¡Nos vemos pronto!"
    )


def draft_review_message(res: dict[str, Any]) -> str:
    """Short post-checkout review ask (24h after check-out)."""
    name = (res.get("guest_name") or "").split(" ")[0] or ""
    hello = f"¡Hola {name}!" if name else "¡Hola!"
    return (
        f"{hello} Gracias por tu estadía en Valizas Hostel. "
        "Si te gustó, nos ayudaría muchísimo una reseña rápida en Google: "
        "https://g.page/r/valizas-hostel/review — ¡gracias!"
    )
