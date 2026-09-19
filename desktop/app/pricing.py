"""Pricing and room matching."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from . import db
from .config import ROOMS


def parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha inválida: {value}")


def nights_between(check_in: date, check_out: date) -> int:
    if check_out <= check_in:
        raise ValueError("La salida debe ser posterior a la entrada")
    return (check_out - check_in).days


def rate_bucket(room_id: str) -> str:
    room = next((r for r in ROOMS if r["id"] == room_id), None)
    if room and room.get("bucket"):
        return str(room["bucket"])
    if "Comp" in room_id or room_id.startswith("Hab_4") or "dorm" in room_id:
        return "dorm"
    if room_id in ("Hab_Priv_2", "Hab_Dob_Priv", "Hab_Dob_Priv_2", "doble"):
        return "doble"
    return "suite"


def nightly_price(room_id: str, day: date, mode: str = "mid") -> float:
    rates = {r["month"]: r for r in db.list_rates()}
    row = rates.get(day.month)
    if not row:
        raise ValueError(f"Sin tarifa para el mes {day.month}")
    bucket = rate_bucket(room_id)
    lo = float(row[f"{bucket}_min"])
    hi = float(row[f"{bucket}_max"])
    if mode == "min":
        return lo
    if mode == "max":
        return hi
    return round((lo + hi) / 2, 2)


def quote_stay(room_id: str, check_in: date, check_out: date, mode: str = "mid") -> dict[str, Any]:
    nights = nights_between(check_in, check_out)
    total = 0.0
    breakdown: list[dict[str, Any]] = []
    day = check_in
    while day < check_out:
        price = nightly_price(room_id, day, mode=mode)
        total += price
        breakdown.append({"date": day.isoformat(), "price": price, "season_month": day.month})
        day += timedelta(days=1)
    return {
        "nights": nights,
        "total_usd": round(total, 2),
        "avg_night_usd": round(total / nights, 2) if nights else 0,
        "breakdown": breakdown,
    }


def rooms_for_guests(guests: int) -> list[dict[str, Any]]:
    if guests < 1:
        raise ValueError("Cantidad de personas inválida")
    return [r for r in db.list_rooms() if r["capacity"] >= guests]


def is_shared(room: dict[str, Any]) -> bool:
    return str(room.get("kind") or "") == "compartida"


def peak_beds_occupied(
    room_id: str,
    check_in: date,
    check_out: date,
    *,
    exclude_id: int | None = None,
) -> int:
    """Max beds taken on any night in [check_in, check_out)."""
    overlaps = db.overlapping_reservations(
        room_id, check_in.isoformat(), check_out.isoformat(), exclude_id=exclude_id
    )
    if not overlaps:
        return 0
    peak = 0
    day = check_in
    while day < check_out:
        day_s = day.isoformat()
        used = 0
        for o in overlaps:
            if o["check_in"] <= day_s < o["check_out"]:
                used += int(o["guests"] or 0)
        peak = max(peak, used)
        day += timedelta(days=1)
    return peak


def beds_remaining(
    room: dict[str, Any],
    check_in: date,
    check_out: date,
    *,
    exclude_id: int | None = None,
) -> int:
    cap = int(room["capacity"])
    if not is_shared(room):
        overlaps = db.overlapping_reservations(
            room["id"], check_in.isoformat(), check_out.isoformat(), exclude_id=exclude_id
        )
        return 0 if overlaps else cap
    used = peak_beds_occupied(room["id"], check_in, check_out, exclude_id=exclude_id)
    return max(0, cap - used)


def apply_stay_modifiers(
    base_price: float,
    nights: int,
    guests: int,
    children: int = 0,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply long-stay and child discounts on top of an already-computed total.

    - Long stay: if nights >= settings.long_stay_nights (default 7), discount
      settings.long_stay_discount_pct (default 10%) off the whole total.
    - Children: only meaningful when base_price scales per person (dorms). If
      children > 0, that share of the total (base_price / guests * children)
      is re-priced at settings.child_rate_pct (default 50%) of the adult rate.
    """
    settings = settings or {}
    price = float(base_price)
    children = max(0, int(children or 0))

    long_stay_nights = int(settings.get("long_stay_nights", 7))
    long_stay_discount_usd = 0.0
    if nights >= long_stay_nights and price > 0:
        pct = float(settings.get("long_stay_discount_pct", 10)) / 100.0
        long_stay_discount_usd = round(price * pct, 2)
        price -= long_stay_discount_usd

    child_discount_usd = 0.0
    if children and guests:
        per_person = base_price / guests
        child_pct = float(settings.get("child_rate_pct", 50)) / 100.0
        full_child_share = per_person * children
        discounted_child_share = full_child_share * child_pct
        child_discount_usd = round(full_child_share - discounted_child_share, 2)
        price -= child_discount_usd

    price = round(max(price, 0.0), 2)
    return {
        "price_usd": price,
        "long_stay_discount_usd": long_stay_discount_usd,
        "child_discount_usd": child_discount_usd,
    }


def rooms_combo_suggestion(guests: int) -> str:
    """Suggest a familiar + compartida combo for groups too big for one room."""
    if guests < 1:
        return ""
    rooms = db.list_rooms()
    if any(int(r["capacity"]) >= guests for r in rooms):
        return ""
    familiares = sorted(
        (r for r in rooms if r.get("kind") == "privada" and int(r["capacity"]) >= 4),
        key=lambda r: -int(r["capacity"]),
    )
    dorms = sorted(
        (r for r in rooms if r.get("kind") == "compartida"),
        key=lambda r: -int(r["capacity"]),
    )
    if not familiares or not dorms:
        return "Para ese grupo no hay combinación armada; consultanos directo."
    fam = familiares[0]
    remaining = max(0, guests - int(fam["capacity"]))
    dorm = next((d for d in dorms if int(d["capacity"]) >= remaining), dorms[0])
    beds = min(remaining, int(dorm["capacity"])) if remaining else 0
    if beds <= 0:
        return f"Para {guests} personas: {fam['name']} (hasta {fam['capacity']})."
    return (
        f"Para {guests} personas no entra en una sola habitación. Sugerencia: "
        f"{fam['name']} (hasta {fam['capacity']}) + {dorm['name']} ({beds} camas)."
    )


def validate_booking(
    *,
    guest_name: str,
    guests: int,
    room_id: str,
    check_in: date,
    check_out: date,
    exclude_id: int | None = None,
    adults: int | None = None,
    children: int = 0,
    whole_dorm: bool = False,
) -> dict[str, Any]:
    guest_name = (guest_name or "").strip()
    if len(guest_name) < 2:
        raise ValueError("Falta el nombre del huésped")
    room = db.get_room(room_id)
    if not room:
        raise ValueError("Habitación inexistente")

    children = max(0, int(children or 0))
    if adults is not None:
        guests = int(adults) + children
    else:
        guests = int(guests)

    shared = is_shared(room)
    capacity = int(room["capacity"])

    if whole_dorm:
        if not shared:
            raise ValueError("Solo se puede reservar completa una habitación compartida")
        guests = capacity
        children = 0

    if guests < 1:
        raise ValueError("Cantidad de personas inválida")
    if guests > capacity:
        if shared:
            raise ValueError(
                f"La compartida tiene {capacity} camas; son {guests}. No entra."
            )
        raise ValueError(
            f"{room['name']} es hasta {capacity} personas; pediste {guests}."
        )
    nights = nights_between(check_in, check_out)
    remaining = beds_remaining(room, check_in, check_out, exclude_id=exclude_id)
    if guests > remaining:
        if shared:
            raise ValueError(
                f"En esa compartida quedan {remaining} camas (de {capacity}); pediste {guests}."
            )
        raise ValueError("Sin disponibilidad en esas fechas.")
    settings = db.load_settings()
    quote = quote_stay(room_id, check_in, check_out, mode=settings.get("price_mode", "mid"))
    # Dorm rates are per person (p/p) on the site
    base_price = quote["total_usd"]
    if shared:
        base_price = round(base_price * guests, 2)

    modifiers = apply_stay_modifiers(
        base_price,
        nights,
        guests,
        children=children if shared else 0,
        settings=settings,
    )
    price = modifiers["price_usd"]

    deposit_pct = float(settings.get("deposit_pct", 0.3))
    deposit_usd = round(price * deposit_pct, 2)

    result = {
        "guest_name": guest_name,
        "guests": guests,
        "adults": (guests - children) if children else (adults if adults is not None else guests),
        "children": children,
        "room_id": room_id,
        "room": room,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "nights": nights,
        "price_usd": price,
        "deposit_usd": deposit_usd,
        "beds_remaining_after": remaining - guests,
        "quote": quote,
        "long_stay_discount_usd": modifiers["long_stay_discount_usd"],
        "child_discount_usd": modifiers["child_discount_usd"],
        "whole_dorm": whole_dorm,
    }
    if shared:
        result["price_per_person"] = round(price / guests, 2) if guests else 0.0
    return result
