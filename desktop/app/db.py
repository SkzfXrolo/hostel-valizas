"""SQLite persistence for reservations, rates and settings."""
from __future__ import annotations

import csv
import json
import re
import secrets
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from .config import DATA_DIR, DB_PATH, DEFAULT_RATES, ROOMS, SETTINGS_PATH

# Allowed reservation lifecycle states. SQLite doesn't enforce this via a CHECK
# constraint (would require a table rebuild); callers should validate against it.
RESERVATION_STATUSES = {
    "provisional",
    "confirmed",
    "checked_in",
    "checked_out",
    "cancelled",
    "no_show",
}

# New reservation columns introduced after the original schema; added via
# best-effort ALTER TABLE so existing databases upgrade in place.
_RESERVATION_NEW_COLUMNS: dict[str, str] = {
    "internal_notes": "TEXT",
    "bed_note": "TEXT",
    "deposit_usd": "REAL",
    "adults": "INTEGER",
    "children": "INTEGER",
    "confirm_token": "TEXT",
    "lang": "TEXT",
    "reminded_at": "TEXT",
    "reviewed_at": "TEXT",
}

_RATE_FIELDS = (
    "season",
    "suite_min",
    "suite_max",
    "doble_min",
    "doble_max",
    "dorm_min",
    "dorm_max",
)

_WA_CHAT_FIELDS = {
    "tag",
    "paused",
    "last_catalog_at",
    "photo_sent_at",
    "photo_room",
    "upsell_sent",
    "lang",
    "sleep_notified_at",
}


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_reservation_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(reservations)").fetchall()}
    for col, coltype in _RESERVATION_NEW_COLUMNS.items():
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE reservations ADD COLUMN {col} {coltype}")
            except sqlite3.OperationalError:
                pass


def _migrate_wa_chat_columns(conn: sqlite3.Connection) -> None:
    try:
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(wa_chats)").fetchall()}
    except sqlite3.OperationalError:
        return
    extras = {
        "sleep_notified_at": "TEXT",
        "photo_sent_at": "TEXT",
        "photo_room": "TEXT",
        "last_catalog_at": "TEXT",
        "upsell_sent": "INTEGER NOT NULL DEFAULT 0",
        "lang": "TEXT",
        "tag": "TEXT",
        "paused": "INTEGER NOT NULL DEFAULT 0",
        "updated_at": "TEXT",
    }
    for col, coltype in extras.items():
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE wa_chats ADD COLUMN {col} {coltype}")
            except sqlite3.OperationalError:
                pass


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS rooms (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              capacity INTEGER NOT NULL,
              photo TEXT NOT NULL,
              kind TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS rates (
              month INTEGER PRIMARY KEY CHECK(month BETWEEN 1 AND 12),
              season TEXT NOT NULL,
              suite_min REAL NOT NULL,
              suite_max REAL NOT NULL,
              doble_min REAL NOT NULL,
              doble_max REAL NOT NULL,
              dorm_min REAL NOT NULL,
              dorm_max REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reservations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              guest_name TEXT NOT NULL,
              guests INTEGER NOT NULL,
              room_id TEXT NOT NULL,
              check_in TEXT NOT NULL,
              check_out TEXT NOT NULL,
              nights INTEGER NOT NULL,
              price_usd REAL NOT NULL,
              status TEXT NOT NULL DEFAULT 'confirmed',
              source TEXT NOT NULL DEFAULT 'manual',
              whatsapp TEXT,
              notes TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(room_id) REFERENCES rooms(id)
            );

            CREATE INDEX IF NOT EXISTS idx_res_dates ON reservations(check_in, check_out);
            CREATE INDEX IF NOT EXISTS idx_res_room ON reservations(room_id);

            CREATE TABLE IF NOT EXISTS rate_history (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              month INTEGER NOT NULL,
              field TEXT NOT NULL,
              old_value TEXT,
              new_value TEXT,
              changed_at TEXT NOT NULL,
              who TEXT
            );

            CREATE TABLE IF NOT EXISTS wa_chats (
              jid TEXT PRIMARY KEY,
              tag TEXT,
              paused INTEGER NOT NULL DEFAULT 0,
              last_catalog_at TEXT,
              photo_sent_at TEXT,
              photo_room TEXT,
              upsell_sent INTEGER NOT NULL DEFAULT 0,
              lang TEXT,
              sleep_notified_at TEXT,
              updated_at TEXT
            );
            """
        )

        _migrate_wa_chat_columns(conn)
        _migrate_reservation_columns(conn)

        existing = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM rooms").fetchall()}
        catalog_ids = {room["id"] for room in ROOMS}
        for room in ROOMS:
            if room["id"] in existing:
                conn.execute(
                    """
                    UPDATE rooms
                    SET name = ?, capacity = ?, photo = ?, kind = ?, active = 1
                    WHERE id = ?
                    """,
                    (room["name"], room["capacity"], room["photo"], room["kind"], room["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO rooms(id, name, capacity, photo, kind, active) VALUES (?,?,?,?,?,1)",
                    (room["id"], room["name"], room["capacity"], room["photo"], room["kind"]),
                )
        for old_id in existing:
            if old_id not in catalog_ids:
                conn.execute("UPDATE rooms SET active = 0 WHERE id = ?", (old_id,))

        rate_count = conn.execute("SELECT COUNT(*) AS c FROM rates").fetchone()["c"]
        if rate_count == 0:
            for month, row in DEFAULT_RATES.items():
                conn.execute(
                    """
                    INSERT INTO rates(month, season, suite_min, suite_max, doble_min, doble_max, dorm_min, dorm_max)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        month,
                        row["season"],
                        row["suite"][0],
                        row["suite"][1],
                        row["doble"][0],
                        row["doble"][1],
                        row["dorm"][0],
                        row["dorm"][1],
                    ),
                )


def load_settings() -> dict[str, Any]:
    from .config import DEFAULT_SETTINGS

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
        return dict(DEFAULT_SETTINGS)
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def list_rooms(active_only: bool = True) -> list[dict[str, Any]]:
    with db() as conn:
        sql = "SELECT * FROM rooms"
        if active_only:
            sql += " WHERE active = 1"
        sql += " ORDER BY capacity, name"
        return [dict(r) for r in conn.execute(sql).fetchall()]


def get_room(room_id: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        return dict(row) if row else None


def list_rates() -> list[dict[str, Any]]:
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM rates ORDER BY month").fetchall()]


def upsert_rate(month: int, data: dict[str, Any], who: str = "") -> None:
    with db() as conn:
        old = conn.execute("SELECT * FROM rates WHERE month = ?", (month,)).fetchone()
        conn.execute(
            """
            INSERT INTO rates(month, season, suite_min, suite_max, doble_min, doble_max, dorm_min, dorm_max)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(month) DO UPDATE SET
              season=excluded.season,
              suite_min=excluded.suite_min,
              suite_max=excluded.suite_max,
              doble_min=excluded.doble_min,
              doble_max=excluded.doble_max,
              dorm_min=excluded.dorm_min,
              dorm_max=excluded.dorm_max
            """,
            (
                month,
                data["season"],
                data["suite_min"],
                data["suite_max"],
                data["doble_min"],
                data["doble_max"],
                data["dorm_min"],
                data["dorm_max"],
            ),
        )
        if old:
            now = datetime.now().isoformat(timespec="seconds")
            for field in _RATE_FIELDS:
                old_v = old[field]
                new_v = data.get(field, old_v)
                if str(old_v) != str(new_v):
                    conn.execute(
                        """
                        INSERT INTO rate_history(month, field, old_value, new_value, changed_at, who)
                        VALUES (?,?,?,?,?,?)
                        """,
                        (month, field, str(old_v), str(new_v), now, who or ""),
                    )


def log_rate_change(month: int, field: str, old_value: Any, new_value: Any, who: str = "") -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO rate_history(month, field, old_value, new_value, changed_at, who)
            VALUES (?,?,?,?,?,?)
            """,
            (month, field, str(old_value), str(new_value), datetime.now().isoformat(timespec="seconds"), who or ""),
        )


def update_rate(month: int, field: str, new_value: Any, who: str = "") -> None:
    """Update a single rate field and record the change in rate_history."""
    if field not in _RATE_FIELDS:
        raise ValueError(f"Campo de tarifa inválido: {field}")
    with db() as conn:
        row = conn.execute("SELECT * FROM rates WHERE month = ?", (month,)).fetchone()
        if not row:
            raise ValueError(f"No hay tarifa para el mes {month}")
        old_value = row[field]
        conn.execute(f"UPDATE rates SET {field} = ? WHERE month = ?", (new_value, month))
        conn.execute(
            """
            INSERT INTO rate_history(month, field, old_value, new_value, changed_at, who)
            VALUES (?,?,?,?,?,?)
            """,
            (month, field, str(old_value), str(new_value), datetime.now().isoformat(timespec="seconds"), who or ""),
        )


def rate_history(month: int | None = None, limit: int = 200) -> list[dict[str, Any]]:
    with db() as conn:
        sql = "SELECT * FROM rate_history"
        params: list[Any] = []
        if month is not None:
            sql += " WHERE month = ?"
            params.append(month)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def overlapping_reservations(
    room_id: str,
    check_in: str,
    check_out: str,
    exclude_id: int | None = None,
) -> list[dict[str, Any]]:
    """Inclusive check_in, exclusive check_out (hotel style)."""
    with db() as conn:
        sql = """
          SELECT * FROM reservations
          WHERE room_id = ?
            AND status NOT IN ('cancelled', 'no_show')
            AND check_in < ?
            AND check_out > ?
        """
        params: list[Any] = [room_id, check_out, check_in]
        if exclude_id is not None:
            sql += " AND id != ?"
            params.append(exclude_id)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _normalize_whatsapp(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits or None


def _generate_confirm_token() -> str:
    return secrets.token_urlsafe(8)


def create_reservation(payload: dict[str, Any]) -> int:
    room_id = payload["room_id"]
    check_in = str(payload["check_in"])
    check_out = str(payload["check_out"])
    guests = int(payload["guests"])

    with db() as conn:
        # BEGIN IMMEDIATE grabs the write lock up front so the availability
        # re-check below and the insert happen atomically (avoids a race
        # between two near-simultaneous bookings for the same beds). The
        # availability logic mirrors pricing.beds_remaining/peak_beds_occupied;
        # it's duplicated here (instead of importing pricing) to avoid a
        # circular import and to keep it on this single connection/transaction.
        conn.execute("BEGIN IMMEDIATE")

        room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room:
            raise ValueError("Habitación inexistente")

        overlaps = conn.execute(
            """
            SELECT check_in, check_out, guests FROM reservations
            WHERE room_id = ? AND status NOT IN ('cancelled', 'no_show')
              AND check_in < ? AND check_out > ?
            """,
            (room_id, check_out, check_in),
        ).fetchall()

        capacity = int(room["capacity"])
        if str(room["kind"]) == "compartida":
            day = date.fromisoformat(check_in)
            end = date.fromisoformat(check_out)
            peak = 0
            cursor = day
            while cursor < end:
                d_s = cursor.isoformat()
                used = sum(int(o["guests"] or 0) for o in overlaps if o["check_in"] <= d_s < o["check_out"])
                peak = max(peak, used)
                cursor += timedelta(days=1)
            remaining = max(0, capacity - peak)
            if guests > remaining:
                raise ValueError(
                    f"En esa compartida quedan {remaining} camas (de {capacity}); pediste {guests}."
                )
        else:
            if overlaps:
                raise ValueError("Sin disponibilidad en esas fechas.")

        confirm_token = payload.get("confirm_token") or _generate_confirm_token()
        whatsapp = _normalize_whatsapp(payload.get("whatsapp"))

        cur = conn.execute(
            """
            INSERT INTO reservations(
              guest_name, guests, room_id, check_in, check_out, nights,
              price_usd, status, source, whatsapp, notes, created_at,
              internal_notes, bed_note, deposit_usd, adults, children,
              confirm_token, lang
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                payload["guest_name"],
                guests,
                room_id,
                check_in,
                check_out,
                payload["nights"],
                payload["price_usd"],
                payload.get("status", "confirmed"),
                payload.get("source", "manual"),
                whatsapp,
                payload.get("notes"),
                datetime.now().isoformat(timespec="seconds"),
                payload.get("internal_notes"),
                payload.get("bed_note"),
                payload.get("deposit_usd"),
                payload.get("adults"),
                payload.get("children"),
                confirm_token,
                payload.get("lang"),
            ),
        )
        return int(cur.lastrowid)


def list_reservations(
    month: int | None = None,
    year: int | None = None,
    include_cancelled: bool = False,
) -> list[dict[str, Any]]:
    with db() as conn:
        sql = "SELECT r.*, rm.name AS room_name FROM reservations r JOIN rooms rm ON rm.id = r.room_id WHERE 1=1"
        params: list[Any] = []
        if not include_cancelled:
            sql += " AND r.status != 'cancelled'"
        if year is not None and month is not None:
            start = f"{year:04d}-{month:02d}-01"
            if month == 12:
                end = f"{year + 1:04d}-01-01"
            else:
                end = f"{year:04d}-{month + 1:02d}-01"
            sql += " AND r.check_in < ? AND r.check_out > ?"
            params.extend([end, start])
        sql += " ORDER BY r.check_in, r.guest_name"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# Alias kept for callers/spec that refer to this as "list_reservations_for_month".
list_reservations_for_month = list_reservations


def reservations_on_day(day: date) -> list[dict[str, Any]]:
    d = day.isoformat()
    with db() as conn:
        rows = conn.execute(
            """
            SELECT r.*, rm.name AS room_name FROM reservations r
            JOIN rooms rm ON rm.id = r.room_id
            WHERE r.status != 'cancelled'
              AND r.check_in <= ?
              AND r.check_out > ?
            ORDER BY rm.capacity, r.guest_name
            """,
            (d, d),
        ).fetchall()
        return [dict(r) for r in rows]


def update_reservation_status(res_id: int, status: str) -> None:
    if status not in RESERVATION_STATUSES:
        raise ValueError(f"Estado inválido: {status}")
    with db() as conn:
        conn.execute("UPDATE reservations SET status = ? WHERE id = ?", (status, res_id))


def cancel_reservation(res_id: int) -> None:
    update_reservation_status(res_id, "cancelled")


def delete_reservation(res_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM reservations WHERE id = ?", (res_id,))


def search_reservations(q: str) -> list[dict[str, Any]]:
    q = (q or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    with db() as conn:
        rows = conn.execute(
            """
            SELECT r.*, rm.name AS room_name FROM reservations r
            JOIN rooms rm ON rm.id = r.room_id
            WHERE r.guest_name LIKE ? OR r.whatsapp LIKE ? OR r.notes LIKE ?
               OR r.internal_notes LIKE ? OR CAST(r.id AS TEXT) = ?
            ORDER BY r.check_in DESC
            LIMIT 200
            """,
            (like, like, like, like, q),
        ).fetchall()
        return [dict(r) for r in rows]


def export_reservations_csv(path: Path, month: int | None = None, year: int | None = None) -> Path:
    rows = list_reservations(month=month, year=year, include_cancelled=True)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "guest_name",
        "guests",
        "adults",
        "children",
        "room_id",
        "room_name",
        "check_in",
        "check_out",
        "nights",
        "price_usd",
        "deposit_usd",
        "status",
        "source",
        "whatsapp",
        "notes",
        "internal_notes",
        "bed_note",
        "created_at",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def backup_db(dest_dir: Path) -> Path:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"valizas_reservas_{stamp}.db"
    src_conn = sqlite3.connect(DB_PATH)
    dest_conn = sqlite3.connect(dest)
    try:
        src_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        src_conn.close()
    return dest


def restore_db(src: Path) -> None:
    src = Path(src)
    if not src.exists():
        raise ValueError("No se encontró el archivo de respaldo")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, DB_PATH)


def daily_summary(day: date | None = None) -> dict[str, Any]:
    d = (day or date.today()).isoformat()
    with db() as conn:
        consultations = conn.execute(
            """
            SELECT COUNT(*) AS c FROM reservations
            WHERE source LIKE 'whatsapp%' AND substr(created_at, 1, 10) = ?
            """,
            (d,),
        ).fetchone()["c"]
        bookings = conn.execute(
            """
            SELECT COUNT(*) AS c FROM reservations
            WHERE status != 'cancelled' AND substr(created_at, 1, 10) = ?
            """,
            (d,),
        ).fetchone()["c"]
        cancelled = conn.execute(
            """
            SELECT COUNT(*) AS c FROM reservations
            WHERE status = 'cancelled' AND substr(created_at, 1, 10) = ?
            """,
            (d,),
        ).fetchone()["c"]
    return {
        "day": d,
        "consultations": int(consultations),
        "bookings": int(bookings),
        "cancelled": int(cancelled),
    }


def beds_occupancy_for_night(room_id: str, day_iso: str) -> int:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT guests FROM reservations
            WHERE room_id = ? AND status NOT IN ('cancelled', 'no_show')
              AND check_in <= ? AND check_out > ?
            """,
            (room_id, day_iso, day_iso),
        ).fetchall()
        return sum(int(r["guests"] or 0) for r in rows)


def dorm_panel(day_iso: str) -> list[dict[str, Any]]:
    with db() as conn:
        rooms = conn.execute(
            "SELECT id, name, capacity FROM rooms WHERE kind = 'compartida' AND active = 1 ORDER BY capacity"
        ).fetchall()
    panel: list[dict[str, Any]] = []
    for room in rooms:
        capacity = int(room["capacity"])
        occupied = beds_occupancy_for_night(room["id"], day_iso)
        panel.append(
            {
                "room_id": room["id"],
                "name": room["name"],
                "capacity": capacity,
                "occupied": occupied,
                "free": max(0, capacity - occupied),
            }
        )
    return panel


def get_wa_chat(jid: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM wa_chats WHERE jid = ?", (jid,)).fetchone()
        return dict(row) if row else None


def save_wa_chat(jid: str, **fields: Any) -> None:
    if not jid:
        raise ValueError("Falta el identificador de chat")
    unknown = set(fields) - _WA_CHAT_FIELDS
    if unknown:
        raise ValueError(f"Campos desconocidos: {', '.join(sorted(unknown))}")
    now = datetime.now().isoformat(timespec="seconds")
    with db() as conn:
        existing = conn.execute("SELECT jid FROM wa_chats WHERE jid = ?", (jid,)).fetchone()
        if existing:
            if fields:
                cols = ", ".join(f"{k} = ?" for k in fields)
                params = list(fields.values()) + [now, jid]
                conn.execute(f"UPDATE wa_chats SET {cols}, updated_at = ? WHERE jid = ?", params)
            else:
                conn.execute("UPDATE wa_chats SET updated_at = ? WHERE jid = ?", (now, jid))
        else:
            cols = ["jid", "updated_at"] + list(fields.keys())
            placeholders = ", ".join("?" for _ in cols)
            params = [jid, now] + list(fields.values())
            conn.execute(f"INSERT INTO wa_chats({', '.join(cols)}) VALUES ({placeholders})", params)


def is_chat_paused(jid: str) -> bool:
    chat = get_wa_chat(jid)
    return bool(chat and chat.get("paused"))


def set_chat_paused(jid: str, paused: bool) -> None:
    save_wa_chat(jid, paused=1 if paused else 0)


def set_chat_tag(jid: str, tag: str) -> None:
    save_wa_chat(jid, tag=tag)
