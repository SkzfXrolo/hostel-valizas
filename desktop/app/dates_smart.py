"""Relative Spanish date parsing for the WhatsApp flow.

Covers phrases guests actually type: "este finde", "puente", "semana santa",
"la noche del 10 de agosto", "salgo el 15". Complements `ai_parser`, which
handles explicit dd/mm dates via the model.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from .config import MONTHS_ES

_MONTH_NAME_TO_NUM = {name.lower(): i + 1 for i, name in enumerate(MONTHS_ES)}
_MONTH_NAME_TO_NUM["setiembre"] = 9  # common Rioplatense spelling

_MONTH_ABBR = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
}

_WEEKDAY_FRIDAY = 4  # Monday=0 ... Sunday=6


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _month_from_name(name: str | None) -> int | None:
    if not name:
        return None
    name = name.strip().lower()
    if name in _MONTH_NAME_TO_NUM:
        return _MONTH_NAME_TO_NUM[name]
    return _MONTH_ABBR.get(name[:3])


def _next_weekday(base: date, weekday: int, *, include_today: bool = True) -> date:
    days_ahead = weekday - base.weekday()
    if days_ahead < 0 or (days_ahead == 0 and not include_today):
        days_ahead += 7
    return base + timedelta(days=days_ahead)


def _easter_sunday(year: int) -> date:
    """Western Easter Sunday via the Anonymous Gregorian (Meeus/Jones/Butcher) algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _semana_santa(today: date) -> tuple[date, date]:
    """Holy week (Thursday through Monday) surrounding Easter Sunday."""
    sunday = _easter_sunday(today.year)
    check_in = sunday - timedelta(days=3)  # Jueves Santo
    if check_in < today:
        sunday = _easter_sunday(today.year + 1)
        check_in = sunday - timedelta(days=3)
    check_out = sunday + timedelta(days=1)  # Lunes de Pascua
    return check_in, check_out


def _resolve_day_month(day: int, month: int | None, ref: date) -> date | None:
    """Next date matching `day`/`month` on/after `ref`. If `month` is None, use the
    next month (from `ref`) that contains that day-of-month."""
    if month:
        year = ref.year
        try:
            d = date(year, month, day)
        except ValueError:
            return None
        if d < ref:
            try:
                d = date(year + 1, month, day)
            except ValueError:
                return None
        return d

    year, mo = ref.year, ref.month
    for _ in range(13):
        try:
            d = date(year, mo, day)
        except ValueError:
            d = None
        if d and d >= ref:
            return d
        mo += 1
        if mo > 12:
            mo = 1
            year += 1
    return None


def parse_relative_dates(
    text: str, today: date | None = None
) -> tuple[date | None, date | None]:
    """Resolve fuzzy weekend/holiday phrases to (check_in, check_out).

    Supports: "este finde" / "este fin de semana" / "el finde" (Fri→Sun, 2
    nights), "puente" (Fri→Mon long weekend, 3 nights), "semana santa"
    (Holy Thursday → Easter Monday). Returns (None, None) if nothing matched.
    """
    today = today or date.today()
    lower = _normalize(text)

    if "semana santa" in lower:
        return _semana_santa(today)

    if "puente" in lower:
        friday = _next_weekday(today, _WEEKDAY_FRIDAY)
        return friday, friday + timedelta(days=3)

    if "finde" in lower or "fin de semana" in lower:
        friday = _next_weekday(today, _WEEKDAY_FRIDAY)
        return friday, friday + timedelta(days=2)

    return None, None


def parse_noche_del(
    text: str, today: date | None = None
) -> tuple[date | None, date | None]:
    """Parse "noche del 10" / "la noche del 10 de agosto" -> (check_in, check_out).

    `check_out` is always `check_in + 1 day` (a single-night stay).
    """
    today = today or date.today()
    lower = _normalize(text)
    m = re.search(r"noche\s+del\s+(\d{1,2})(?:\s+de\s+([a-záéíóúñ]+))?", lower)
    if not m:
        return None, None

    day = int(m.group(1))
    month_name = m.group(2)
    month = _month_from_name(month_name)
    if month_name and not month:
        return None, None

    check_in = _resolve_day_month(day, month, today)
    if not check_in:
        return None, None
    return check_in, check_in + timedelta(days=1)


def parse_salgo_el(
    text: str,
    check_in_hint: date | None = None,
    today: date | None = None,
) -> tuple[date | None, date | None]:
    """Parse "salgo el 15" / "salgo el 15 de agosto" -> (check_in_hint, check_out).

    `check_in_hint` (if provided, e.g. from a prior "noche del ...") is used as
    the reference point and passed through unchanged; only the departure date
    is resolved here.
    """
    today = today or date.today()
    lower = _normalize(text)
    m = re.search(r"salgo\s+el\s+(\d{1,2})(?:\s+de\s+([a-záéíóúñ]+))?", lower)
    if not m:
        return check_in_hint, None

    day = int(m.group(1))
    month_name = m.group(2)
    month = _month_from_name(month_name)
    if month_name and not month:
        return check_in_hint, None

    ref = check_in_hint or today
    check_out = _resolve_day_month(day, month, ref)
    if not check_out:
        return check_in_hint, None
    if check_in_hint and check_out <= check_in_hint:
        return check_in_hint, None
    return check_in_hint, check_out
