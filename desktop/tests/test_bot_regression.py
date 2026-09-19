"""Regression tests for the WhatsApp bot (Valizas Hostel).

Short, focused tests covering the flows most likely to break silently:
greetings, capacity limits, shared-dorm bed math, consult-only quotes, FAQ
answers, relative-date parsing, language detection, room photos and the
pause/sleep safety switches.

Run with:  pytest desktop/tests/test_bot_regression.py -q   (from repo root)
       or:  pytest -q                                       (from desktop/)

Uses the *real* app.db (SQLite file under desktop/data/) rather than a fully
isolated temp DB, since several code paths resolve paths at import time
(module-level constants derived from `config`). To keep this test-safe:
  - every test that touches settings goes through the `_base_settings`
    autouse fixture, which snapshots + restores the real settings.json
    after each test (forcing ai_provider="rules" so nothing hits the
    network / real Groq key during the run);
  - every test that creates a WhatsApp session/reservation uses the `jid`
    fixture, which generates a throwaway phone number and deletes any
    session/reservation/wa_chat tied to it afterwards.
"""
from __future__ import annotations

import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import ai_parser, config, dates_smart, db, i18n_bot, media_util, pricing, wa_flow  # noqa: E402

db.init_db()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _base_settings():
    """Force deterministic, offline-safe settings for every test, then restore."""
    original = db.load_settings()
    forced = dict(original)
    forced.update(
        {
            "ai_provider": "rules",  # no network calls during the test run
            "pause_all_replies": False,
            "bot_sleep_start": "00:00",
            "bot_sleep_end": "00:00",  # start == end => sleep window disabled
            "catalog_cooldown_sec": 0,
            "photo_cooldown_sec": 0,
        }
    )
    db.save_settings(forced)
    yield
    db.save_settings(original)


@pytest.fixture()
def jid():
    """A throwaway WhatsApp jid, cleaned up (session + chat + reservations) after the test."""
    phone = f"5989{uuid.uuid4().int % 10**7:07d}"
    j = f"{phone}@s.whatsapp.net"
    yield j
    try:
        sessions = wa_flow._load_sessions()
        if j in sessions:
            del sessions[j]
            wa_flow._save_sessions(sessions)
    except Exception:  # noqa: BLE001
        pass
    try:
        with db.db() as conn:
            conn.execute("DELETE FROM wa_chats WHERE jid = ?", (j,))
            conn.execute("DELETE FROM reservations WHERE whatsapp = ?", (phone,))
    except Exception:  # noqa: BLE001
        pass


def _future_range(days_ahead: int = 60, nights: int = 2) -> tuple[date, date]:
    ci = date.today() + timedelta(days=days_ahead)
    return ci, ci + timedelta(days=nights)


# ---------------------------------------------------------------------------
# Greetings / language
# ---------------------------------------------------------------------------


def test_greet_hola_short_reply(jid):
    out = wa_flow.handle_message("Hola", jid=jid)
    assert out["reply"]
    assert "hola" in out["reply"].lower()
    assert "fecha" in out["reply"].lower()
    assert out["booked"] is False


def test_greet_variants_detected():
    for text in ("hola!", "Buenos días", "hello", "buenas tardes"):
        assert wa_flow._is_bare_greeting(text), text
    assert not wa_flow._is_bare_greeting("hola quiero reservar 2 personas")


def test_lang_detect_english_hello():
    assert i18n_bot.detect_lang("Hello, how much is a private room?") == "en"


def test_lang_detect_portuguese():
    assert i18n_bot.detect_lang("Olá, quanto custa o quarto?") == "pt"


def test_lang_detect_spanish_default():
    assert i18n_bot.detect_lang("Hola, cuánto sale la doble?") == "es"


def test_lang_detect_empty_defaults_to_spanish():
    assert i18n_bot.detect_lang("") == "es"


# ---------------------------------------------------------------------------
# Capacity / rooms
# ---------------------------------------------------------------------------


def test_ten_guests_no_single_room_fits():
    msg, ids = wa_flow.format_rooms_catalog(10)
    assert ids == []
    assert "no tenemos" in msg.lower()


def test_ten_guests_rejects_hab_comp_8_capacity_error():
    ci, co = _future_range()
    with pytest.raises(ValueError) as exc:
        pricing.validate_booking(
            guest_name="PYTEST Capacity",
            guests=10,
            room_id="Hab_Comp_8",
            check_in=ci,
            check_out=co,
        )
    msg = str(exc.value)
    assert "8" in msg
    assert "10" in msg


def test_rooms_for_guests_excludes_undersized():
    rooms = wa_flow.rooms_for_guests(6)
    assert all(r["capacity"] >= 6 for r in rooms)
    assert any(r["id"] == "Hab_Comp_8" for r in rooms)
    assert not any(r["id"] == "Hab_Dob" for r in rooms)  # capacity 2 < 6


def test_rooms_combo_suggestion_for_group_of_ten():
    combo = pricing.rooms_combo_suggestion(10)
    assert combo
    assert "10 personas" in combo


def test_shared_beds_3_plus_3_fits_in_8(jid):
    ci, co = _future_range(days_ahead=120, nights=2)
    phone = jid.split("@")[0]
    p1 = pricing.validate_booking(
        guest_name="PYTEST Group A", guests=3, room_id="Hab_Comp_8", check_in=ci, check_out=co
    )
    rid1 = db.create_reservation({**p1, "source": "pytest", "whatsapp": phone, "notes": "t"})
    p2 = pricing.validate_booking(
        guest_name="PYTEST Group B", guests=3, room_id="Hab_Comp_8", check_in=ci, check_out=co
    )
    rid2 = db.create_reservation({**p2, "source": "pytest", "whatsapp": phone, "notes": "t"})
    assert rid1 and rid2
    assert p2["beds_remaining_after"] == 2  # 8 - 3 - 3


def test_shared_beds_overbook_rejected(jid):
    ci, co = _future_range(days_ahead=150, nights=2)
    phone = jid.split("@")[0]
    p1 = pricing.validate_booking(
        guest_name="PYTEST Group C", guests=6, room_id="Hab_Comp_8", check_in=ci, check_out=co
    )
    db.create_reservation({**p1, "source": "pytest", "whatsapp": phone, "notes": "t"})
    with pytest.raises(ValueError):
        pricing.validate_booking(
            guest_name="PYTEST Group D", guests=3, room_id="Hab_Comp_8", check_in=ci, check_out=co
        )


# ---------------------------------------------------------------------------
# Quote / consult-only flow
# ---------------------------------------------------------------------------


def _sample_payload():
    ci, co = _future_range(days_ahead=200, nights=3)
    return pricing.validate_booking(
        guest_name="PYTEST Quote", guests=3, room_id="Hab_Comp_8", check_in=ci, check_out=co
    )


def test_consult_only_uses_consult_cta_not_confirm():
    payload = _sample_payload()
    reply = wa_flow._quote_reply(payload, lang="es", consult_only=True)
    assert "duda" in reply.lower()
    assert "confirmamos" not in reply.lower()


def test_normal_quote_uses_confirm_cta():
    payload = _sample_payload()
    reply = wa_flow._quote_reply(payload, lang="es", consult_only=False)
    assert "confirmamos" in reply.lower()


def test_quote_reply_shared_room_mentions_per_person():
    payload = _sample_payload()
    reply = wa_flow._quote_reply(payload, lang="es")
    assert "p/p" in reply or "camas" in reply.lower()


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------


def test_faq_parking_detect_and_answer():
    key = wa_flow.detect_faq("¿hay estacionamiento cerca?")
    assert key == "parking"
    assert wa_flow.faq_answer(key, "es") == config.HOSTEL_FAQ["parking"]


def test_faq_checkin_hours_detected():
    key = wa_flow.detect_faq("a qué hora es el check-in?")
    assert key == "checkin"
    assert "14:00" in wa_flow.faq_answer(key, "es")


def test_faq_pool_answer_no_pileta():
    key = wa_flow.detect_faq("tienen pileta?")
    assert key == "pool"
    assert "no tenemos piscina" in wa_flow.faq_answer(key, "es").lower()


def test_faq_cancellation_detected_and_matches_settings():
    key = wa_flow.detect_faq("cuál es la política de cancelación?")
    assert key == "cancellation"
    settings = db.load_settings()
    assert "48h" in settings["cancellation_policy"]
    assert "48h" in wa_flow.faq_answer(key, "es")


def test_faq_via_handle_message(jid):
    out = wa_flow.handle_message("¿tienen estacionamiento?", jid=jid)
    assert out["reply"] == config.HOSTEL_FAQ["parking"]


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------


def test_dates_smart_finde_returns_two_dates():
    ci, co = dates_smart.parse_relative_dates("este finde")
    assert ci is not None and co is not None
    assert ci.weekday() == 4  # Friday
    assert (co - ci).days == 2


def test_dates_smart_puente_three_nights():
    ci, co = dates_smart.parse_relative_dates("nos vamos el puente")
    assert (co - ci).days == 3


def test_dates_smart_noche_del_single_night():
    ci, co = dates_smart.parse_noche_del("la noche del 10 de agosto")
    assert ci.day == 10 and ci.month == 8
    assert (co - ci).days == 1


def test_dates_smart_no_match_returns_none():
    ci, co = dates_smart.parse_relative_dates("hola como estas")
    assert ci is None and co is None


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------


def test_photo_path_exists_for_hab_fam():
    path = media_util.room_photo_path("Hab_Fam")
    assert path is not None
    assert path.is_file()


def test_photo_path_exists_for_all_catalog_rooms():
    missing = [r["id"] for r in config.ROOMS if not media_util.room_photo_path(r["id"])]
    assert not missing, f"Rooms missing a photo file: {missing}"


def test_room_extra_photos_no_crash():
    extra = media_util.room_extra_photos("Hab_Comp_8")
    assert isinstance(extra, list)


# ---------------------------------------------------------------------------
# Pause / sleep safety switches
# ---------------------------------------------------------------------------


def test_pause_all_replies_returns_paused(jid):
    settings = db.load_settings()
    settings["pause_all_replies"] = True
    db.save_settings(settings)
    out = wa_flow.handle_message("Hola", jid=jid)
    assert out["paused"] is True
    assert out["reply"] is None


def test_chat_level_pause_returns_paused(jid):
    db.set_chat_paused(jid, True)
    out = wa_flow.handle_message("Hola", jid=jid)
    assert out["paused"] is True


def test_sleep_window_blocks_replies(jid):
    settings = db.load_settings()
    settings["bot_sleep_start"] = "00:00"
    settings["bot_sleep_end"] = "23:59"
    db.save_settings(settings)
    out = wa_flow.handle_message("Hola", jid=jid)
    assert out.get("sleeping") is True
    assert out["reply"]


def test_sleep_window_still_allows_confirm(jid):
    settings = db.load_settings()
    settings["bot_sleep_start"] = "00:00"
    settings["bot_sleep_end"] = "23:59"
    db.save_settings(settings)
    out = wa_flow.handle_message("confirmo", jid=jid)
    assert out.get("sleeping") is not True


# ---------------------------------------------------------------------------
# End-to-end booking flow
# ---------------------------------------------------------------------------


def test_full_booking_flow_creates_reservation(jid):
    r1 = wa_flow.handle_message(
        "Somos 2, del 10 al 12 de septiembre, queremos la doble suite", jid=jid
    )
    assert r1["quoted"] is True
    assert r1["phase"] == "quoting"

    r2 = wa_flow.handle_message("confirmo", jid=jid)
    assert r2["booked"] is True
    assert r2["res_id"]

    rows = [r for r in db.list_reservations() if r["id"] == r2["res_id"]]
    assert len(rows) == 1
    assert rows[0]["room_id"] in ("Hab_priv", "Hab_Dob")  # both match the "doble suite" phrasing
    assert rows[0]["guests"] == 2


def test_cancel_reservation_flow(jid):
    wa_flow.handle_message("Somos 2, del 20 al 22 de noviembre, la doble suite", jid=jid)
    booked = wa_flow.handle_message("confirmo", jid=jid)
    assert booked["booked"] is True
    rid = booked["res_id"]

    cancelled = wa_flow.handle_message("cancelar la reserva por favor", jid=jid)
    assert cancelled["cancelled"] is True

    row = next(r for r in db.list_reservations(include_cancelled=True) if r["id"] == rid)
    assert row["status"] == "cancelled"


def test_do_book_prevents_duplicate_within_60s(jid):
    draft = {
        "guest_name": "PYTEST Dup Guest",
        "guests": 2,
        "room_id": "Hab_Dob",
        "check_in": "2026-11-05",
        "check_out": "2026-11-07",
    }

    def _out():
        return {
            "reply": None,
            "booked": False,
            "res_id": None,
            "parsed": {},
            "phase": None,
            "error": None,
            "quoted": False,
            "cancelled": False,
            "photo_paths": [],
            "ai_engine": None,
            "lang": "es",
        }

    sess = {"_key": jid, "draft": dict(draft)}
    r1 = wa_flow._do_book(sess, jid, "", _out(), "confirmo", lang="es")
    assert r1["booked"] is True
    rid = r1["res_id"]

    # Simulate a retried/duplicate WhatsApp delivery of the same confirmation:
    # a fresh session snapshot that still carries the pre-reset draft plus the
    # bookkeeping fields _do_book just wrote (sig/timestamp/res_id).
    sess2 = {
        "_key": jid,
        "draft": dict(draft),
        "last_book_at": sess["last_book_at"],
        "last_book_sig": sess["last_book_sig"],
        "last_res_id": sess["last_res_id"],
    }
    r2 = wa_flow._do_book(sess2, jid, "", _out(), "confirmo", lang="es")
    assert r2["booked"] is True
    assert r2.get("duplicate") is True
    assert r2["res_id"] == rid


# ---------------------------------------------------------------------------
# ai_parser safeguards
# ---------------------------------------------------------------------------


def test_ai_parser_engine_always_present():
    for text in ("hola", "somos 2 del 1 al 3 de enero", ""):
        result = ai_parser.extract_reservation(text)
        assert result.get("engine")


def test_ai_parser_extract_with_rules_has_engine():
    result = ai_parser.extract_with_rules("hola quiero info")
    assert result["engine"] == "rules"


def test_ai_parser_strips_room_not_mentioned_in_text():
    data = {"room_id": "Hab_Comp_8", "guests": 2, "guest_name": None, "check_in": None, "check_out": None}
    merged = ai_parser._merge_with_rules(data, "quiero reservar para 2 personas", "test-engine")
    assert merged["room_id"] is None


def test_ai_parser_keeps_room_when_actually_mentioned():
    data = {"room_id": "Hab_Fam", "guests": 4, "guest_name": None, "check_in": None, "check_out": None}
    merged = ai_parser._merge_with_rules(data, "somos 4, queremos la familiar", "test-engine")
    assert merged["room_id"] == "Hab_Fam"


def test_ai_parser_dates_smart_hook_overrides_finde():
    result = {"check_in": "2099-01-01", "check_out": "2099-01-02"}
    fixed = ai_parser._dates_smart_hook("nos vamos este finde", result)
    ci = date.fromisoformat(fixed["check_in"])
    assert ci.weekday() == 4
    assert fixed["check_in"] != "2099-01-01"


# ---------------------------------------------------------------------------
# Voucher + reminders
# ---------------------------------------------------------------------------


def test_voucher_save_writes_html_and_txt(tmp_path):
    from app import voucher

    res = {
        "id": 12345,
        "guest_name": "PYTEST Voucher Guest",
        "room_name": "Compartida 8 camas",
        "check_in": "2026-09-10",
        "check_out": "2026-09-12",
        "nights": 2,
        "guests": 3,
        "price_usd": 150.0,
        "deposit_usd": 45.0,
        "status": "confirmed",
        "whatsapp": "59891234567",
    }
    path = voucher.save_voucher(res, tmp_path)
    assert path.exists()
    assert path.suffix in (".html", ".pdf")
    if path.suffix == ".html":
        txt_path = path.with_suffix(".txt")
        assert txt_path.exists()
        assert "USD 150" in txt_path.read_text(encoding="utf-8")


def test_reminders_due_reminders_finds_confirmed_check_in_in_2_days(jid):
    from app import reminders

    ci = date.today() + timedelta(days=reminders.REMINDER_DAYS_BEFORE)
    co = ci + timedelta(days=2)
    payload = pricing.validate_booking(
        guest_name="PYTEST Reminder Guest",
        guests=1,
        room_id="Hab_priv",
        check_in=ci,
        check_out=co,
    )
    phone = jid.split("@")[0]
    rid = db.create_reservation({**payload, "source": "pytest", "whatsapp": phone, "notes": "t"})
    try:
        due = reminders.due_reminders()
        assert any(r["id"] == rid for r in due)
        reminders.mark_reminded(rid)
        due_after = reminders.due_reminders()
        assert not any(r["id"] == rid for r in due_after)
    finally:
        db.delete_reservation(rid)


def test_draft_reminder_and_review_messages_are_short_and_named():
    from app import reminders

    res = {"guest_name": "Ana Perez", "room_name": "Doble suite", "check_in": "2026-09-10"}
    reminder = reminders.draft_reminder_message(res)
    review = reminders.draft_review_message(res)
    assert "Ana" in reminder
    assert "Ana" in review
    assert len(reminder.splitlines()) <= 3
    assert len(review.splitlines()) <= 3


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
