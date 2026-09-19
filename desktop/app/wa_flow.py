"""Conversational WhatsApp booking flow — quote ≠ reserve."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from . import ai_parser, dates_smart, db, i18n_bot, media_util, pricing
from .config import ASSETS_ROOMS, DATA_DIR, HOSTEL_FAQ, HOSTEL_FAQ_EN, HOSTEL_FAQ_PT, ROOMS

SESSIONS_PATH = DATA_DIR / "wa_sessions.json"

# Phases: idle → collecting → choosing_room → quoting → confirm → (booked|idle)
CONFIRM_WORDS = (
    "confirmo",
    "confirmá",
    "confirma",
    "confirmado",
    "sí reservo",
    "si reservo",
    "sí, reservo",
    "si, reservo",
    "reservar ahora",
    "dale reservá",
    "dale reserva",
    "ok reservo",
    "ok, reservo",
    "sí quiero esa",
    "si quiero esa",
    "la quiero",
    "cierro",
    "cerramos",
)
CANCEL_WORDS = (
    "cancelar",
    "cancelá",
    "cancela",
    "anular",
    "anulá",
    "no quiero reservar",
    "olvidalo",
    "olvidalo",
    "dejá",
    "deja quieto",
)
BACK_WORDS = ("atrás", "atras", "volver", "retroceder", "anterior", "menu", "menú")
QUOTE_WORDS = (
    "precio",
    "precios",
    "cuesta",
    "cuánto",
    "cuanto",
    "cotiz",
    "consulta",
    "consultar",
    "info",
    "información",
    "informacion",
    "solo quiero saber",
    "sólo quiero saber",
    "me pasás el precio",
    "me pasas el precio",
    "tarif",
)
ROOMS_WORDS = (
    "habitacion",
    "habitación",
    "habitaciones",
    "cuartos",
    "opciones",
    "qué hay",
    "que hay",
    "catalogo",
    "catálogo",
    "tipo de habit",
    "tipos de habit",
    "qué tipo",
    "que tipo",
    "qué opciones",
    "que opciones",
    "disponib",
)
BOOKING_WORDS = (
    "me gustaría reservar",
    "me gustaria reservar",
    "quiero reservar",
    "quisiera reservar",
    "necesito reservar",
    "reservar",
    "hacer una reserva",
    "una reserva",
)
PHOTO_WORDS = (
    "foto",
    "fotos",
    "imagen",
    "imágenes",
    "imagenes",
    "mandame foto",
    "pásame foto",
    "pasame foto",
    "mandá foto",
    "manda foto",
    "cómo se ve",
    "como se ve",
    "mostrame",
    "mostrá",
)
MORE_PHOTOS_WORDS = (
    "más fotos",
    "mas fotos",
    "otra foto",
    "otras fotos",
    "más imágenes",
    "mas imagenes",
    "alguna más",
    "alguna mas",
)
HOUSE_PHOTOS_WORDS = (
    "fotos de la casa",
    "foto de la casa",
    "fotos del hostel",
    "foto del hostel",
    "cómo es el hostel",
    "como es el hostel",
    "fotos generales",
    "fotos de afuera",
)
ROOM_Q_WORDS = (
    "baño",
    "bano",
    "aire",
    "locker",
    "lockers",
    "terraza",
    "balcón",
    "balcon",
    "vista",
    "cama",
    "camas",
    "frigobar",
    "smart",
    "tv",
    "incluye",
    "cómo es",
    "como es",
    "qué tiene",
    "que tiene",
    "tiene ",
    "hay ",
    "cuántas",
    "cuantas",
    "capacidad",
    "personas entra",
    "duda",
    "pregunt",
)
# Greeting-only messages ("hola", "buen día", "hi", "oi", ...) → short greet + ask dates.
_GREETING_RE = re.compile(
    r"^(hola+|holis+|buen[oa]?s?\s*(d[ií]as?|tardes|noches)?|hello+|hi|hey+|"
    r"oi|ol[áa]|bom\s*dia|boa\s*(tarde|noite))[\s!¡.,]*$",
    re.IGNORECASE,
)
CONSULT_ONLY_WORDS = (
    "solo consulto",
    "sólo consulto",
    "solo quiero saber",
    "sólo quiero saber",
    "no reservo",
    "no voy a reservar",
    "todavía no reservo",
    "todavia no reservo",
    "es solo para averiguar",
    "es solo consulta",
    "por ahora solo pregunto",
    "por ahora solo consulto",
)
MULTI_ROOM_WORDS = (
    "2 habitaciones",
    "dos habitaciones",
    "2 cuartos",
    "dos cuartos",
    "2 dormitorios",
    "dos dormitorios",
    "dos piezas",
    "2 piezas",
)
WHOLE_DORM_WORDS = (
    "toda la compartida",
    "el dormi completo",
    "el dormitorio completo",
    "toda la habitación compartida",
    "todo el dormitorio",
    "compartida entera",
    "dormitorio entero",
)
LATER_BYE_WORDS = (
    "después te aviso",
    "despues te aviso",
    "luego te digo",
    "te aviso",
    "más adelante te digo",
    "mas adelante te digo",
    "después confirmo",
    "despues confirmo",
    "capaz más adelante",
    "capaz mas adelante",
)
HANDOFF_WORDS = (
    "hablar con leo",
    "hablar con rubén",
    "hablar con ruben",
    "persona real",
    "un humano",
    "hablar con alguien",
    "hablar con una persona",
    "atención humana",
    "atencion humana",
    "quiero hablar con alguien",
)
# General FAQ intents answered straight from config.HOSTEL_FAQ* (no room context needed).
FAQ_TOPICS: list[tuple[str, tuple[str, ...]]] = [
    (
        "checkin",
        (
            "hora de check-in",
            "hora de entrada",
            "a qué hora entro",
            "a que hora entro",
            "a qué hora llego",
            "a que hora llego",
            "check-in",
            "check in",
        ),
    ),
    (
        "checkout",
        (
            "hora de check-out",
            "hora de salida",
            "a qué hora salgo",
            "a que hora salgo",
            "check-out",
            "checkout",
        ),
    ),
    ("parking", ("estacionamiento", "cochera", "parking", "dónde estaciono", "donde estaciono")),
    ("pool", ("pileta", "piscina", "pool")),
    ("breakfast", ("desayuno", "breakfast")),
    ("pets", ("mascota", "mascotas", "perro", "perros", "gato", "gatos", "pet friendly", "pets")),
    (
        "location",
        (
            "ubicación",
            "ubicacion",
            "dónde queda",
            "donde queda",
            "dirección",
            "direccion",
            "cómo llego",
            "como llego",
            "mapa",
            "location",
            "address",
            "where are you",
        ),
    ),
    ("wifi", ("wifi", "wi-fi", "wi fi")),
    ("deposit", ("seña", "sena", "depósito", "deposito", "adelanto para reservar", "deposit")),
    ("cancellation", ("cancelaci", "cancellation")),
]
_FAQ_BY_LANG = {"es": HOSTEL_FAQ, "en": HOSTEL_FAQ_EN, "pt": HOSTEL_FAQ_PT}

UPSELL_LINES = {
    "es": "Dato: el desayuno ya está incluido en el precio.",
    "en": "Heads up: breakfast is already included in the price.",
    "pt": "Detalhe: o café da manhã já está incluído no preço.",
}
_CONFIRM_CTA = {
    "es": "¿Confirmamos? Decime sí.",
    "en": "Shall we confirm? Just say yes.",
    "pt": "Confirmamos? Me diga sim.",
}
_CONSULT_CTA = {
    "es": "Cualquier duda avisame.",
    "en": "Any questions, just let me know.",
    "pt": "Qualquer dúvida, me chama.",
}
_MIXED_DORM_NOTE = {
    "es": " Es dormitorio mixto.",
    "en": " It's a mixed dorm.",
    "pt": " É dormitório misto.",
}
_ADULTS_CHILDREN_RE = re.compile(
    r"(\d+)\s*adult\w*\s*(?:y|e|,|\+|con)?\s*(\d+)\s*(?:ni[nñ]\w*|nene\w*|nena\w*|child\w*|kid\w*)",
    re.IGNORECASE,
)

# Ficha corta por habitación (para dudas + pie de foto)
ROOM_FACTS: dict[str, dict[str, Any]] = {
    "Hab_priv": {
        "bath": "baño privado",
        "beds": "cama doble · 2 personas",
        "amenities": ["baño privado", "ropa de cama", "desayuno incluido", "Wi‑Fi"],
    },
    "Hab_Dob": {
        "bath": "baño privado",
        "beds": "cama doble · 2 personas",
        "amenities": ["baño privado", "ropa de cama", "desayuno incluido", "Wi‑Fi"],
    },
    "Hab_Fam": {
        "bath": "baño privado",
        "beds": "sommier 2 plazas + cucheta · hasta 4",
        "amenities": ["baño privado", "hasta 4 personas", "desayuno incluido", "Wi‑Fi"],
    },
    "Apart_suite_4": {
        "bath": "baño privado",
        "beds": "hasta 4 personas",
        "amenities": [
            "terraza privada",
            "aire acondicionado",
            "frigobar",
            "Smart TV",
            "desayuno incluido",
            "Wi‑Fi",
        ],
    },
    "Hab_Priv_2": {
        "bath": "baño compartido",
        "beds": "cama doble · 2 personas",
        "amenities": ["vista al mar", "balcón y terraza", "desayuno incluido", "Wi‑Fi"],
    },
    "Hab_Dob_Priv": {
        "bath": "baño compartido",
        "beds": "cama doble · 2 personas",
        "amenities": ["habitación privada", "desayuno incluido", "Wi‑Fi"],
    },
    "Hab_Dob_Priv_2": {
        "bath": "baño compartido",
        "beds": "cama doble · 2 personas",
        "amenities": ["habitación privada", "desayuno incluido", "Wi‑Fi"],
    },
    "Hab_4": {
        "bath": "baños compartidos",
        "beds": "4 camas · compartida (se reserva por cama)",
        "amenities": ["balcón y terraza", "lockers", "desayuno incluido", "Wi‑Fi"],
    },
    "Hab_Comp_6": {
        "bath": "baños compartidos",
        "beds": "6 camas · compartida (se reserva por cama)",
        "amenities": ["balcón y terraza", "lockers", "desayuno incluido", "Wi‑Fi"],
    },
    "Hab_Comp_8": {
        "bath": "baños compartidos",
        "beds": "8 camas · compartida (se reserva por cama)",
        "amenities": ["lockers", "sábanas y mantas", "desayuno incluido", "Wi‑Fi"],
    },
}


def _load_sessions() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SESSIONS_PATH.exists():
        return {}
    try:
        return json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save_sessions(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _session_key(jid: str, from_name: str = "") -> str:
    return (jid or from_name or "local").strip() or "local"


def get_session(jid: str, from_name: str = "") -> dict[str, Any]:
    key = _session_key(jid, from_name)
    all_s = _load_sessions()
    sess = all_s.get(key) or {
        "phase": "idle",
        "draft": {},
        "history": [],
        "last_res_id": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    sess["_key"] = key
    return sess


def save_session(sess: dict[str, Any]) -> None:
    key = sess.pop("_key", None) or "local"
    all_s = _load_sessions()
    sess["updated_at"] = datetime.now().isoformat(timespec="seconds")
    all_s[key] = {k: v for k, v in sess.items() if not k.startswith("_")}
    _save_sessions(all_s)
    sess["_key"] = key


def reset_draft(sess: dict[str, Any], keep_name: bool = True) -> None:
    name = (sess.get("draft") or {}).get("guest_name") if keep_name else None
    sess["draft"] = {"guest_name": name} if name else {}
    sess["phase"] = "idle"
    sess["history"] = []
    sess["consult_only"] = False
    sess["whole_dorm_request"] = False


def short_room_label(room: dict[str, Any]) -> str:
    labels = {
        "Hab_priv": "Doble con baño privado",
        "Hab_Dob": "Doble baño privado",
        "Hab_Fam": "Familiar (sommier + cucheta)",
        "Apart_suite_4": "Apartamento c/ terraza",
        "Hab_Priv_2": "Doble con vista al mar",
        "Hab_Dob_Priv": "Doble baño compartido",
        "Hab_Dob_Priv_2": "Doble baño compartido",
        "Hab_4": "Compartida 4 camas",
        "Hab_Comp_6": "Compartida 6 camas",
        "Hab_Comp_8": "Compartida 8 camas",
    }
    return labels.get(room["id"], room["name"])


def room_photo_path(room_id: str) -> Path | None:
    """Prefer JPG for WhatsApp; stay under assets/rooms."""
    room = next((r for r in ROOMS if r["id"] == room_id), None)
    if not room:
        return None
    stem = Path(str(room.get("photo") or room_id)).stem
    root = ASSETS_ROOMS.resolve()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = (root / f"{stem}{ext}").resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.is_file():
            return path
    return None


def room_blurb_line(room_id: str) -> str:
    room = next((r for r in ROOMS if r["id"] == room_id), None)
    facts = ROOM_FACTS.get(room_id) or {}
    name = short_room_label(room) if room else room_id
    bits = [name]
    if facts.get("beds"):
        bits.append(str(facts["beds"]))
    if facts.get("bath"):
        bits.append(str(facts["bath"]))
    am = facts.get("amenities") or []
    if am:
        bits.append(", ".join(am[:3]))
    return " · ".join(bits)


def answer_room_question(text: str, room_id: str) -> str:
    """Respuesta corta a dudas sobre una habitación concreta."""
    lower = text.lower()
    room = next((r for r in ROOMS if r["id"] == room_id), None)
    facts = ROOM_FACTS.get(room_id) or {}
    name = short_room_label(room) if room else room_id
    cap = int(room["capacity"]) if room else 0
    kind = (room or {}).get("kind")

    if _contains_any(lower, ("baño", "bano")):
        return f"{name}: {facts.get('bath', 'consultá con recepción')}."
    if _contains_any(lower, ("cama", "camas", "cuántas", "cuantas", "capacidad", "personas")):
        if kind == "compartida":
            return f"{name}: {cap} camas. Reservás las que necesites; el resto queda libre."
        return f"{name}: {facts.get('beds', f'hasta {cap} personas')}."
    if _contains_any(lower, ("locker", "lockers")):
        if any("locker" in a.lower() for a in (facts.get("amenities") or [])):
            return f"Sí, {name} tiene lockers."
        return "En las compartidas hay lockers; en privadas guardás en la habitación."
    if _contains_any(lower, ("terraza", "balcón", "balcon", "vista")):
        am = " ".join(facts.get("amenities") or []).lower()
        if "terraza" in am or "vista" in am or "balcón" in am:
            return f"Sí: {name} — {facts.get('beds', '')}. " + ", ".join(
                a for a in (facts.get("amenities") or []) if any(
                    k in a.lower() for k in ("terraza", "vista", "balcón", "balcon")
                )
            )
        return f"{name} no destaca terraza/vista; te puedo pasar otra opción."
    if _contains_any(lower, ("aire", "frigobar", "smart", "tv")):
        am = facts.get("amenities") or []
        hit = [a for a in am if any(k in a.lower() for k in ("aire", "frigobar", "smart", "tv"))]
        if hit:
            return f"Sí: {', '.join(hit)}."
        return f"En {name} no está listado aire/frigobar/TV; el apartamento sí los tiene."
    if _contains_any(lower, ("incluye", "qué tiene", "que tiene", "cómo es", "como es", "tiene")):
        return room_blurb_line(room_id)

    # IA corta solo con ficha (sin inventar)
    try:
        system = (
            "Respondé por WhatsApp en 1-2 líneas, español rioplatense, sin códigos internos. "
            "Usá SOLO los datos de la ficha. Si no está, decí que no lo sabés y ofrecé otra duda."
        )
        user = (
            f"Ficha: {room_blurb_line(room_id)}\n"
            f"Capacidad: {cap}. Tipo: {kind}.\n"
            f"Pregunta del huésped: {text}"
        )
        ai = ai_parser._chat_completion(system, user)  # noqa: SLF001
        if ai:
            return ai.strip()
    except Exception:  # noqa: BLE001
        pass
    return f"{room_blurb_line(room_id)}. ¿Qué más querés saber?"


def attach_room_photo(
    out: dict[str, Any],
    sess: dict[str, Any],
    room_id: str,
    *,
    jid: str = "",
    force: bool = False,
) -> None:
    """Attach a compressed/watermarked room photo, respecting the photo cooldown."""
    path = media_util.room_photo_path(room_id)
    if not path:
        return
    settings = db.load_settings()
    cooldown = int(settings.get("photo_cooldown_sec", 600) or 0)
    now = datetime.now()

    if not force and cooldown > 0:
        last_iso = None
        if sess.get("photo_sent_for") == room_id:
            last_iso = sess.get("photo_sent_at")
        elif jid:
            try:
                chat = db.get_wa_chat(jid)
            except Exception:  # noqa: BLE001
                chat = None
            if chat and chat.get("photo_room") == room_id:
                last_iso = chat.get("photo_sent_at")
        if last_iso:
            try:
                last_dt = datetime.fromisoformat(str(last_iso))
                if (now - last_dt).total_seconds() < cooldown:
                    sess["photo_sent_for"] = room_id
                    sess["focus_room"] = room_id
                    return
            except ValueError:
                pass

    ready = str(media_util.prepare_wa_image(path))
    out["photo_path"] = ready
    paths = out.setdefault("photo_paths", [])
    if ready not in paths:
        paths.append(ready)
    now_iso = now.isoformat(timespec="seconds")
    sess["photo_sent_for"] = room_id
    sess["photo_sent_at"] = now_iso
    sess["focus_room"] = room_id
    if jid:
        try:
            db.save_wa_chat(jid, photo_room=room_id, photo_sent_at=now_iso)
        except Exception:  # noqa: BLE001
            pass


def rooms_for_guests(guests: int | None = None) -> list[dict[str, Any]]:
    """Only rooms that fit. Never fall back to undersized options."""
    if guests:
        return [r for r in ROOMS if r["capacity"] >= guests]
    return list(ROOMS)


def format_rooms_catalog(guests: int | None = None) -> tuple[str, list[str]]:
    """Short list for WhatsApp. Returns (message, ordered room ids)."""
    rooms = rooms_for_guests(guests)
    if guests and not rooms:
        max_cap = max((r["capacity"] for r in ROOMS), default=0)
        return (
            f"Para {guests} no tenemos una habitación tan grande "
            f"(máx. {max_cap}). ¿Dividen en dos o más?",
            [],
        )
    ids = [r["id"] for r in rooms]
    lines = []
    if guests:
        lines.append(f"Para {guests} personas:")
    else:
        lines.append("Opciones:")
    for i, r in enumerate(rooms, start=1):
        label = short_room_label(r)
        if r.get("kind") == "compartida":
            label = f"{label} (cama suelta)"
        lines.append(f"{i}) {label}")
    lines.append("")
    lines.append("¿Cuál te gusta? (número o nombre)")
    return "\n".join(lines), ids


def pick_room_from_text(text: str, offered: list[str] | None = None) -> str | None:
    """Resolve '2', 'la 3', 'familiar', etc. to a room id."""
    lower = text.lower().strip()
    offered = offered or [r["id"] for r in ROOMS]

    m = re.match(r"^(?:la\s+|el\s+|opci[oó]n\s+|n[uú]mero\s+|#)?(\d{1,2})$", lower)
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(offered):
            return offered[idx]

    # prefer offered list order for alias match
    alias_map = [
        ("Apart_suite_4", ["apart", "apartamento", "suite 4", "apart suite"]),
        ("Hab_Fam", ["familiar", "familia", "sommier", "cucheta"]),
        ("Hab_Priv_2", ["vista", "mar", "terraza"]),
        ("Hab_Comp_8", ["8 camas", "compartida 8", "dorm 8", "ocho"]),
        ("Hab_Comp_6", ["6 camas", "compartida 6", "dorm 6", "seis"]),
        ("Hab_4", ["4 camas", "compartida 4", "dorm 4", "cuatro"]),
        ("Hab_priv", ["baño suite", "suite", "doble suite"]),
        ("Hab_Dob", ["doble baño", "doble con baño"]),
        ("Hab_Dob_Priv", ["baño compartido", "doble compartido"]),
        ("Hab_Dob_Priv_2", ["baño compartido 2"]),
    ]
    for room_id, aliases in alias_map:
        if room_id not in offered:
            continue
        if any(a in lower for a in aliases):
            return room_id
    return None


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(w in lower for w in words)


def _is_bare_greeting(text: str) -> bool:
    cleaned = text.strip()
    return bool(cleaned) and bool(_GREETING_RE.match(cleaned))


def detect_faq(lower: str) -> str | None:
    for key, words in FAQ_TOPICS:
        if _contains_any(lower, words):
            return key
    return None


def faq_answer(key: str, lang: str) -> str:
    table = _FAQ_BY_LANG.get(lang, HOSTEL_FAQ)
    return table.get(key) or HOSTEL_FAQ.get(key, "")


def parse_adults_children(text: str) -> tuple[int, int] | None:
    """Parse '2 adultos y 1 niño' style phrases into (adults, children)."""
    m = _ADULTS_CHILDREN_RE.search(text)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _dates_smart_guess(text: str, draft: dict[str, Any]) -> tuple[date | None, date | None]:
    """Deterministic fill-in for relative date phrases (finde, puente, noche del X...)."""
    ci, co = dates_smart.parse_relative_dates(text)
    if not ci:
        ci, co = dates_smart.parse_noche_del(text)
    if ci and not co:
        _, co2 = dates_smart.parse_salgo_el(text, check_in_hint=ci)
        co = co2 or co
    if not ci:
        hint_in = None
        if draft.get("check_in"):
            try:
                hint_in = date.fromisoformat(str(draft["check_in"]))
            except ValueError:
                hint_in = None
        ci2, co2 = dates_smart.parse_salgo_el(text, check_in_hint=hint_in)
        if co2:
            ci, co = ci2, co2
    return ci, co


def detect_intent(text: str) -> str:
    lower = text.lower().strip()
    if _contains_any(lower, CANCEL_WORDS) or lower in {"no", "nop", "nel"}:
        return "cancel"
    if _contains_any(lower, BACK_WORDS):
        return "back"
    if _contains_any(lower, PHOTO_WORDS):
        return "photo"
    if _contains_any(lower, ROOM_Q_WORDS):
        # no pisar reserva explícita
        if not _contains_any(lower, BOOKING_WORDS + CONFIRM_WORDS):
            return "room_question"
    if _contains_any(lower, ROOMS_WORDS):
        return "rooms"
    if _contains_any(lower, BOOKING_WORDS) and not _contains_any(lower, CONFIRM_WORDS):
        if not _contains_any(lower, ("confirmo", "confirmá", "confirmado", "reservar ahora", "ok reservo")):
            return "booking_start"
    if _contains_any(lower, CONFIRM_WORDS) or lower in {"sí", "si", "ok", "dale", "va", "listo"}:
        return "confirm"
    if _contains_any(lower, QUOTE_WORDS):
        return "quote"
    return "message"


def merge_parsed_into_draft(sess: dict[str, Any], parsed: dict[str, Any], *, allow_room: bool) -> None:
    draft = sess.setdefault("draft", {})
    for key in ("guest_name", "guests", "check_in", "check_out"):
        if parsed.get(key) not in (None, "", 0):
            draft[key] = parsed[key]
    if allow_room and parsed.get("room_id"):
        draft["room_id"] = parsed["room_id"]


def missing_for_quote(draft: dict[str, Any]) -> list[str]:
    need = []
    for k in ("guests", "check_in", "check_out"):
        if not draft.get(k):
            need.append(k)
    return need


def missing_for_book(draft: dict[str, Any]) -> list[str]:
    need = missing_for_quote(draft)
    if not draft.get("room_id"):
        need.append("room_id")
    return need


def try_quote(draft: dict[str, Any]) -> dict[str, Any] | None:
    try:
        room_id = draft.get("room_id")
        if not room_id:
            return None
        guests = int(draft.get("guests") or 1)
        payload = pricing.validate_booking(
            guest_name=draft.get("guest_name") or "Consulta",
            guests=guests,
            room_id=str(room_id),
            check_in=pricing.parse_date(str(draft["check_in"])),
            check_out=pricing.parse_date(str(draft["check_out"])),
            adults=draft.get("adults"),
            children=int(draft.get("children") or 0),
            whole_dorm=bool(draft.get("whole_dorm")),
        )
        return payload
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def push_history(sess: dict[str, Any]) -> None:
    snap = {"phase": sess.get("phase"), "draft": dict(sess.get("draft") or {})}
    hist = sess.setdefault("history", [])
    hist.append(snap)
    if len(hist) > 12:
        del hist[0]


def go_back(sess: dict[str, Any]) -> bool:
    hist = sess.get("history") or []
    if not hist:
        return False
    prev = hist.pop()
    sess["phase"] = prev.get("phase") or "idle"
    sess["draft"] = prev.get("draft") or {}
    return True


def cancel_latest_for_contact(jid: str, from_name: str = "") -> int | None:
    """Cancel most recent active reservation matching WhatsApp jid or guest name."""
    phone = ""
    if jid and "@" in jid:
        phone = jid.split("@")[0]
    with db.db() as conn:
        row = None
        if phone:
            row = conn.execute(
                """
                SELECT id FROM reservations
                WHERE status != 'cancelled' AND (whatsapp LIKE ? OR notes LIKE ?)
                ORDER BY id DESC LIMIT 1
                """,
                (f"%{phone}%", f"%{phone}%"),
            ).fetchone()
        if row is None and from_name:
            row = conn.execute(
                """
                SELECT id FROM reservations
                WHERE status != 'cancelled' AND guest_name = ?
                ORDER BY id DESC LIMIT 1
                """,
                (from_name,),
            ).fetchone()
        if row is None:
            row = conn.execute(
                """
                SELECT id FROM reservations
                WHERE status != 'cancelled' AND source LIKE 'whatsapp%'
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        rid = int(row["id"])
        conn.execute("UPDATE reservations SET status='cancelled' WHERE id=?", (rid,))
        return rid


def _offer_rooms(sess: dict[str, Any], guests: int | None = None) -> str:
    if guests and guests >= 9:
        combo = pricing.rooms_combo_suggestion(guests)
        if combo:
            sess["offered_rooms"] = []
            return combo
    msg, ids = format_rooms_catalog(guests)
    sess["offered_rooms"] = ids
    return msg


def _catalog_recent(sess: dict[str, Any], jid: str) -> bool:
    settings = db.load_settings()
    cooldown = int(settings.get("catalog_cooldown_sec", 300) or 0)
    if cooldown <= 0:
        return False
    last = sess.get("last_catalog_at")
    if not last and jid:
        try:
            chat = db.get_wa_chat(jid)
        except Exception:  # noqa: BLE001
            chat = None
        last = (chat or {}).get("last_catalog_at")
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(str(last))
    except ValueError:
        return False
    return (datetime.now() - last_dt).total_seconds() < cooldown


def _mark_catalog_sent(sess: dict[str, Any], jid: str) -> None:
    now_iso = datetime.now().isoformat(timespec="seconds")
    sess["last_catalog_at"] = now_iso
    if jid:
        try:
            db.save_wa_chat(jid, last_catalog_at=now_iso)
        except Exception:  # noqa: BLE001
            pass


def _offer_catalog(sess: dict[str, Any], jid: str, guests: int | None, lang: str) -> str:
    """Full room catalog, or a short 'already sent' reply if within the cooldown window."""
    if _catalog_recent(sess, jid):
        return i18n_bot.t(lang, "catalog_cooldown")
    catalog = _offer_rooms(sess, guests)
    _mark_catalog_sent(sess, jid)
    return catalog


def _tag(jid: str, tag: str) -> None:
    if not jid:
        return
    try:
        db.set_chat_tag(jid, tag)
    except Exception:  # noqa: BLE001
        pass


def _maybe_upsell(out: dict[str, Any], sess: dict[str, Any], jid: str, lang: str, settings: dict[str, Any]) -> None:
    """Append one soft upsell line after a quote, at most once per chat."""
    if not settings.get("upsell_enabled", True):
        return
    if sess.get("upsell_sent"):
        return
    if jid:
        try:
            chat = db.get_wa_chat(jid)
        except Exception:  # noqa: BLE001
            chat = None
        if chat and chat.get("upsell_sent"):
            sess["upsell_sent"] = True
            return
    line = UPSELL_LINES.get(lang, UPSELL_LINES["es"])
    if out.get("reply"):
        out["reply"] = f"{out['reply']} {line}"
    sess["upsell_sent"] = True
    if jid:
        try:
            db.save_wa_chat(jid, upsell_sent=1)
        except Exception:  # noqa: BLE001
            pass


def _in_sleep_window(settings: dict[str, Any]) -> bool:
    start_s = str(settings.get("bot_sleep_start") or "").strip()
    end_s = str(settings.get("bot_sleep_end") or "").strip()
    if not start_s or not end_s:
        return False
    try:
        start_t = datetime.strptime(start_s, "%H:%M").time()
        end_t = datetime.strptime(end_s, "%H:%M").time()
    except ValueError:
        return False
    if start_t == end_t:
        return False
    now_t = datetime.now().time()
    if start_t < end_t:
        return start_t <= now_t < end_t
    return now_t >= start_t or now_t < end_t


def _room_said_in_text(lower: str) -> bool:
    """True only if the guest named a room type (not amenity questions)."""
    hints = (
        "habitacion",
        "habitación",
        "cuarto",
        "suite",
        "apart",
        "familiar",
        "familia",
        "dorm",
        "compartida",
        "compartido",
        "privada",
        "privado",
        "doble",
        "vista al mar",
        "sommier",
        "cucheta",
        "baño suite",
        "bano suite",
        "baño compartido",
        "bano compartido",
    )
    return any(h in lower for h in hints)


def _friendly_room(room_id: str) -> str:
    meta = next((r for r in ROOMS if r["id"] == room_id), None)
    if meta:
        return short_room_label(meta)
    room = db.get_room(room_id)
    return (room or {}).get("name") or "esa habitación"


def _capacity_mismatch(draft: dict[str, Any]) -> str | None:
    rid = draft.get("room_id")
    guests = draft.get("guests")
    if not rid or not guests:
        return None
    room = next((r for r in ROOMS if r["id"] == rid), None) or db.get_room(str(rid))
    if not room:
        return None
    cap = int(room["capacity"])
    guests_n = int(guests)
    if guests_n <= cap:
        return None
    if room.get("kind") == "compartida":
        return f"Esa compartida tiene {cap} camas; son {guests_n}. No entra."
    return f"Esa habitación es hasta {cap}; son {guests_n}."


def _quote_reply(
    payload: dict[str, Any],
    *,
    lang: str = "es",
    consult_only: bool = False,
    mixed_dorms: bool = True,
) -> str:
    name = _friendly_room(payload["room"]["id"])
    guests = int(payload["guests"])
    nights = int(payload["nights"])
    price = float(payload["price_usd"])
    deposit = payload.get("deposit_usd")
    shared = pricing.is_shared(payload["room"])

    cta_table = _CONSULT_CTA if consult_only else _CONFIRM_CTA
    cta = cta_table.get(lang, cta_table["es"])

    deposit_line = ""
    if deposit:
        deposit_line = {
            "es": f" Seña: USD {deposit:.0f}.",
            "en": f" Deposit: USD {deposit:.0f}.",
            "pt": f" Sinal: USD {deposit:.0f}.",
        }.get(lang, f" Seña: USD {deposit:.0f}.")

    if shared:
        per_person = payload.get("price_per_person")
        pp_bit = f" (USD {per_person:.0f} p/p)" if per_person is not None else ""
        left = payload.get("beds_remaining_after")
        left_bit = f" Quedan {left} libres." if left is not None else ""
        mixed_bit = _MIXED_DORM_NOTE.get(lang, _MIXED_DORM_NOTE["es"]) if mixed_dorms else ""
        return (
            f"{guests} camas en {name}: {nights} noches, *USD {price:.0f}*{pp_bit}."
            f"{left_bit}{mixed_bit}{deposit_line} {cta}"
        )
    return f"{name}: {nights} noches, {guests} pers., *USD {price:.0f}*.{deposit_line} {cta}"


def _draft_sig(draft: dict[str, Any]) -> str:
    keys = ("room_id", "check_in", "check_out", "guests", "guest_name", "adults", "children", "whole_dorm")
    return json.dumps({k: draft.get(k) for k in keys}, sort_keys=True, default=str)


def handle_message(
    text: str,
    *,
    jid: str = "",
    from_name: str = "",
) -> dict[str, Any]:
    """WhatsApp flow: short replies, no codes, quote ≠ book."""
    text = (text or "").strip()
    sess = get_session(jid, from_name)
    lower = text.lower()

    lang = i18n_bot.detect_lang(text) if len(text) > 1 else (sess.get("lang") or "es")
    sess["lang"] = lang
    if jid:
        try:
            db.save_wa_chat(jid, lang=lang)
        except Exception:  # noqa: BLE001
            pass

    settings = db.load_settings()

    if settings.get("pause_all_replies") or (jid and db.is_chat_paused(jid)):
        save_session(sess)
        return {
            "reply": None,
            "booked": False,
            "res_id": None,
            "parsed": {},
            "phase": sess.get("phase"),
            "error": None,
            "quoted": False,
            "cancelled": False,
            "paused": True,
            "photo_paths": [],
            "ai_engine": None,
            "lang": lang,
        }

    quick_confirm_or_cancel = (
        _contains_any(lower, CONFIRM_WORDS)
        or _contains_any(lower, CANCEL_WORDS)
        or lower.strip() in {"sí", "si", "ok", "dale", "va", "listo", "yes"}
    )
    if _in_sleep_window(settings) and not quick_confirm_or_cancel:
        # Avisar UNA sola vez por chat en la ventana de descanso (no spamear)
        already = False
        if jid:
            chat = db.get_wa_chat(jid) or {}
            prev = str(chat.get("sleep_notified_at") or "")
            if prev:
                try:
                    prev_dt = datetime.fromisoformat(prev)
                    # misma noche de sueño: desde start hasta end
                    already = (datetime.now() - prev_dt).total_seconds() < 12 * 3600
                except ValueError:
                    already = False
        save_session(sess)
        if already:
            return {
                "reply": None,
                "booked": False,
                "res_id": None,
                "parsed": {},
                "phase": sess.get("phase"),
                "error": None,
                "quoted": False,
                "cancelled": False,
                "sleeping": True,
                "photo_paths": [],
                "ai_engine": None,
                "lang": lang,
            }
        if jid:
            try:
                db.save_wa_chat(jid, sleep_notified_at=datetime.now().isoformat(timespec="seconds"))
            except Exception:  # noqa: BLE001
                pass
        return {
            "reply": i18n_bot.t(
                lang,
                "sleep_mode",
                start=settings.get("bot_sleep_start", ""),
                end=settings.get("bot_sleep_end", ""),
            ),
            "booked": False,
            "res_id": None,
            "parsed": {},
            "phase": sess.get("phase"),
            "error": None,
            "quoted": False,
            "cancelled": False,
            "sleeping": True,
            "photo_paths": [],
            "ai_engine": None,
            "lang": lang,
        }

    out: dict[str, Any] = {
        "reply": None,
        "booked": False,
        "res_id": None,
        "parsed": {},
        "phase": sess.get("phase"),
        "error": None,
        "quoted": False,
        "cancelled": False,
        "photo_paths": [],
        "ai_engine": None,
        "lang": lang,
    }

    if _contains_any(lower, HANDOFF_WORDS):
        push_history(sess)
        if jid:
            try:
                db.save_wa_chat(jid, paused=1)
            except Exception:  # noqa: BLE001
                pass
        names = settings.get("operator_names") or "el equipo"
        out["reply"] = i18n_bot.t(lang, "human_handoff", names=names)
        out["handoff"] = True
        save_session(sess)
        out["phase"] = sess.get("phase")
        return out

    if _is_bare_greeting(text):
        push_history(sess)
        name_bit = f" {from_name}" if from_name else ""
        out["reply"] = i18n_bot.t(lang, "greet", name=name_bit)
        save_session(sess)
        out["phase"] = sess.get("phase")
        return out

    if _contains_any(lower, MULTI_ROOM_WORDS):
        push_history(sess)
        out["reply"] = i18n_bot.t(lang, "group_flow")
        _tag(jid, "consulta")
        save_session(sess)
        out["phase"] = sess.get("phase")
        return out

    if _contains_any(lower, LATER_BYE_WORDS):
        push_history(sess)
        out["reply"] = i18n_bot.t(lang, "later_bye")
        _tag(jid, "perdido")
        save_session(sess)
        out["phase"] = sess.get("phase")
        return out

    faq_key = detect_faq(lower)
    if faq_key:
        push_history(sess)
        out["reply"] = faq_answer(faq_key, lang)
        _tag(jid, "consulta")
        save_session(sess)
        out["phase"] = sess.get("phase")
        return out

    if _contains_any(lower, CONSULT_ONLY_WORDS):
        sess["consult_only"] = True
    if _contains_any(lower, WHOLE_DORM_WORDS):
        sess["whole_dorm_request"] = True

    intent = detect_intent(text)
    strong_confirm = _contains_any(lower, CONFIRM_WORDS)
    weak_confirm = lower.strip() in {"sí", "si", "ok", "dale", "va", "listo", "yes"}

    if intent == "cancel":
        push_history(sess)
        rid = cancel_latest_for_contact(jid, from_name) or sess.get("last_res_id")
        if rid and ("reserva" in lower or sess.get("phase") == "booked" or sess.get("last_res_id")):
            reset_draft(sess)
            sess["last_res_id"] = None
            save_session(sess)
            out["cancelled"] = True
            out["res_id"] = int(rid)
            out["reply"] = "Listo, cancelada. Si querés otra, avisame fechas y personas."
            out["phase"] = "idle"
            return out
        reset_draft(sess)
        sess["last_res_id"] = None
        save_session(sess)
        out["reply"] = "Ok, paramos. Cuando quieras, mandame fechas y personas."
        out["phase"] = "idle"
        return out

    if intent == "back":
        if go_back(sess):
            save_session(sess)
            out["reply"] = f"Ok, un paso atrás. {_status_line(sess)}"
            out["phase"] = sess.get("phase")
            return out
        reset_draft(sess)
        save_session(sess)
        out["reply"] = "Empezamos de cero. Decime fechas y personas."
        return out

    rel_ci, rel_co = _dates_smart_guess(text, sess.get("draft") or {})
    parsed = ai_parser.extract_reservation(text)
    if not parsed.get("guest_name") and from_name:
        parsed["guest_name"] = from_name
    if rel_ci and not parsed.get("check_in"):
        parsed["check_in"] = rel_ci.isoformat()
    if rel_co and not parsed.get("check_out"):
        parsed["check_out"] = rel_co.isoformat()

    ac = parse_adults_children(text)
    if ac:
        adults, children = ac
        draft0 = sess.setdefault("draft", {})
        draft0["adults"] = adults
        draft0["children"] = children
        if not parsed.get("guests"):
            parsed["guests"] = adults + children

    # Number / nombre corto gana siempre sobre la IA (Groq inventa códigos)
    picked = pick_room_from_text(text, sess.get("offered_rooms"))
    is_bare_number = bool(re.match(r"^(?:la\s+|el\s+|opci[oó]n\s+|n[uú]mero\s+|#)?\d{1,2}$", lower))
    if picked:
        parsed["room_id"] = picked
        # "3" = opción 3, no "3 personas"
        if is_bare_number:
            parsed["guests"] = None
    elif parsed.get("room_id") and not _room_said_in_text(lower):
        # No aceptar habitación inventada por la IA
        parsed["room_id"] = None
    if is_bare_number and sess.get("phase") == "choosing_room" and sess.get("offered_rooms"):
        # Bare numbers while choosing a room are always a room pick, never a guest count.
        parsed["guests"] = None

    out["parsed"] = parsed
    out["ai_engine"] = parsed.get("engine")

    # Foto / dudas de habitación (antes del flujo de reserva)
    if intent in ("photo", "room_question"):
        push_history(sess)
        merge_parsed_into_draft(sess, parsed, allow_room=False)
        if picked:
            sess.setdefault("draft", {})["room_id"] = picked
            sess["focus_room"] = picked

        if intent == "photo" and _contains_any(lower, HOUSE_PHOTOS_WORDS):
            paths = [str(media_util.prepare_wa_image(p)) for p in media_util.house_album_paths()]
            if paths:
                out["photo_paths"] = paths
                out["photo_path"] = paths[0]
                out["reply"] = {
                    "es": "Así es la casa.",
                    "en": "Here's the house.",
                    "pt": "Assim é a casa.",
                }.get(lang, "Así es la casa.")
                _tag(jid, "consulta")
                save_session(sess)
                out["phase"] = sess.get("phase") or "choosing_room"
                return out

        focus = (
            picked
            or (sess.get("draft") or {}).get("room_id")
            or sess.get("focus_room")
        )

        if intent == "photo" and _contains_any(lower, MORE_PHOTOS_WORDS) and focus:
            extra = [str(media_util.prepare_wa_image(p)) for p in media_util.room_extra_photos(focus)]
            if extra:
                out["photo_paths"] = extra
                out["photo_path"] = extra[0]
                out["reply"] = {
                    "es": "Van más fotos.",
                    "en": "Here are more photos.",
                    "pt": "Seguem mais fotos.",
                }.get(lang, "Van más fotos.")
                _tag(jid, "consulta")
                save_session(sess)
                out["phase"] = sess.get("phase") or "choosing_room"
                return out

        if not focus:
            guests = int((sess.get("draft") or {}).get("guests") or 0) or None
            catalog = _offer_catalog(sess, jid, guests, lang)
            save_session(sess)
            out["reply"] = f"¿De qué habitación?\n{catalog}"
            out["phase"] = "choosing_room"
            return out

        sess["focus_room"] = focus
        if intent == "photo":
            out["reply"] = room_blurb_line(focus)
            attach_room_photo(out, sess, focus, jid=jid, force=True)
        else:
            out["reply"] = answer_room_question(text, focus)
            attach_room_photo(out, sess, focus, jid=jid, force=False)
        _tag(jid, "consulta")
        save_session(sess)
        out["phase"] = sess.get("phase") or "choosing_room"
        return out

    push_history(sess)
    merge_parsed_into_draft(sess, parsed, allow_room=True)

    if sess.get("whole_dorm_request"):
        draft_wd = sess.get("draft") or {}
        rid = draft_wd.get("room_id")
        if rid:
            room_meta = next((r for r in ROOMS if r["id"] == rid), None)
            if room_meta and room_meta.get("kind") == "compartida":
                draft_wd["whole_dorm"] = True
                draft_wd["guests"] = room_meta["capacity"]
            sess["whole_dorm_request"] = False

    cap_err = _capacity_mismatch(sess.get("draft") or {})
    if cap_err:
        (sess.get("draft") or {}).pop("room_id", None)
        guests = int((sess.get("draft") or {}).get("guests") or 0) or None
        sess["phase"] = "choosing_room"
        catalog = _offer_catalog(sess, jid, guests, lang)
        save_session(sess)
        out["reply"] = f"{cap_err}\n{catalog}"
        out["phase"] = "choosing_room"
        out["error"] = cap_err
        return out

    if intent in ("rooms", "booking_start") or re.search(r"\b(opciones|tipos de hab)\b", lower):
        guests = int((sess.get("draft") or {}).get("guests") or 0) or None
        sess["phase"] = "choosing_room"
        catalog = _offer_catalog(sess, jid, guests, lang)
        save_session(sess)
        if intent == "booking_start":
            hi = f"¡Hola{(' ' + from_name) if from_name else ''}! "
            out["reply"] = f"{hi}{catalog}"
        else:
            out["reply"] = catalog
        _tag(jid, "consulta")
        out["phase"] = "choosing_room"
        return out

    wants_quote = intent == "quote" or (
        bool(parsed.get("room_id")) and not strong_confirm and sess.get("phase") != "confirm"
    )

    if wants_quote and (sess.get("draft") or {}).get("room_id"):
        miss = missing_for_quote(sess["draft"])
        room_id = str(sess["draft"]["room_id"])
        room_name = _friendly_room(room_id)
        sess["focus_room"] = room_id
        if miss:
            sess["phase"] = "collecting"
            out["reply"] = f"{room_name}, buen gusto. Me falta {_missing_es(miss)}."
            attach_room_photo(out, sess, room_id, jid=jid)
            save_session(sess)
            out["phase"] = "collecting"
            return out

        payload = try_quote(sess["draft"])
        if payload and payload.get("error"):
            out["error"] = payload["error"]
            out["reply"] = f"Eso no me cierra ({payload['error']}). Probá otras fechas."
            save_session(sess)
            return out
        if payload:
            sess["phase"] = "quoting"
            sess["draft"]["quoted_price"] = payload["price_usd"]
            out["quoted"] = True
            out["payload"] = payload
            out["reply"] = _quote_reply(
                payload,
                lang=lang,
                consult_only=bool(sess.get("consult_only")),
                mixed_dorms=bool(settings.get("mixed_dorms", True)),
            )
            _maybe_upsell(out, sess, jid, lang, settings)
            attach_room_photo(out, sess, room_id, jid=jid)
            _tag(jid, "cotizado")
            save_session(sess)
            out["phase"] = "quoting"
            return out

    if strong_confirm or (sess.get("phase") in ("confirm", "quoting") and weak_confirm):
        miss = missing_for_book(sess.get("draft") or {})
        if miss:
            sess["phase"] = "collecting"
            save_session(sess)
            guests = int((sess.get("draft") or {}).get("guests") or 0) or None
            if "room_id" in miss:
                out["reply"] = _offer_catalog(sess, jid, guests, lang)
            else:
                out["reply"] = f"Casi. Me falta {_missing_es(miss)}."
            save_session(sess)
            return out
        if sess.get("phase") in ("quoting", "confirm") or strong_confirm:
            if sess.get("phase") not in ("confirm", "quoting") and not weak_confirm:
                payload = try_quote(sess["draft"])
                if payload and not payload.get("error"):
                    sess["phase"] = "confirm"
                    out["quoted"] = True
                    out["payload"] = payload
                    out["reply"] = _quote_reply(
                        payload,
                        lang=lang,
                        consult_only=bool(sess.get("consult_only")),
                        mixed_dorms=bool(settings.get("mixed_dorms", True)),
                    )
                    _maybe_upsell(out, sess, jid, lang, settings)
                    attach_room_photo(out, sess, str(sess["draft"]["room_id"]), jid=jid)
                    _tag(jid, "cotizado")
                    save_session(sess)
                    out["phase"] = "confirm"
                    return out
            return _do_book(sess, jid, from_name, out, text, lang=lang)

    draft = sess.get("draft") or {}
    miss = missing_for_book(draft)

    if not miss:
        payload = try_quote(draft)
        if payload and not payload.get("error"):
            sess["phase"] = "confirm"
            out["quoted"] = True
            out["payload"] = payload
            out["reply"] = _quote_reply(
                payload,
                lang=lang,
                consult_only=bool(sess.get("consult_only")),
                mixed_dorms=bool(settings.get("mixed_dorms", True)),
            )
            _maybe_upsell(out, sess, jid, lang, settings)
            attach_room_photo(out, sess, str(draft["room_id"]), jid=jid)
            _tag(jid, "cotizado")
            save_session(sess)
            out["phase"] = "confirm"
            return out
        if payload and payload.get("error"):
            out["error"] = payload["error"]
            out["reply"] = f"Uhm, {payload['error']}. Otras fechas?"
            save_session(sess)
            return out

    if "room_id" in miss:
        guests = int(draft.get("guests") or 0) or None
        other = [m for m in miss if m != "room_id"]
        sess["phase"] = "choosing_room"
        catalog = _offer_catalog(sess, jid, guests, lang)
        save_session(sess)
        if other:
            out["reply"] = f"Me falta {_missing_es(other)}.\n\n{catalog}"
        else:
            out["reply"] = catalog
        _tag(jid, "consulta")
        out["phase"] = "choosing_room"
        return out

    sess["phase"] = "collecting"
    save_session(sess)
    if not draft and not any(
        parsed.get(k) for k in ("guests", "check_in", "check_out", "room_id", "guest_name")
    ):
        out["reply"] = i18n_bot.t(lang, "unclear")
    else:
        out["reply"] = f"Dale. Me falta {_missing_es(miss)}."
    out["phase"] = "collecting"
    return out


def _do_book(
    sess: dict[str, Any],
    jid: str,
    from_name: str,
    out: dict[str, Any],
    text: str,
    *,
    lang: str = "es",
) -> dict[str, Any]:
    draft = sess.get("draft") or {}
    sig = _draft_sig(draft)
    last_at = sess.get("last_book_at")
    if last_at and sess.get("last_book_sig") == sig and sess.get("last_res_id"):
        try:
            recent = (datetime.now() - datetime.fromisoformat(str(last_at))).total_seconds() < 60
        except ValueError:
            recent = False
        if recent:
            out["booked"] = True
            out["res_id"] = sess.get("last_res_id")
            out["duplicate"] = True
            out["phase"] = "booked"
            out["reply"] = "Ya quedó anotada, ¡todo en orden!"
            return out
    try:
        payload = pricing.validate_booking(
            guest_name=draft.get("guest_name") or from_name or "Huésped WhatsApp",
            guests=int(draft.get("guests") or 1),
            room_id=str(draft["room_id"]),
            check_in=pricing.parse_date(str(draft["check_in"])),
            check_out=pricing.parse_date(str(draft["check_out"])),
            adults=draft.get("adults"),
            children=int(draft.get("children") or 0),
            whole_dorm=bool(draft.get("whole_dorm")),
        )
        phone = jid.split("@")[0] if jid else None
        res_id = db.create_reservation(
            {
                **payload,
                "source": "whatsapp-confirm",
                "whatsapp": phone,
                "notes": (draft.get("notes") or text)[:500],
                "lang": lang,
            }
        )
        confirm_token = None
        try:
            with db.db() as conn:
                row = conn.execute(
                    "SELECT confirm_token FROM reservations WHERE id = ?", (res_id,)
                ).fetchone()
            confirm_token = row["confirm_token"] if row else None
        except Exception:  # noqa: BLE001
            confirm_token = None

        sess["phase"] = "booked"
        sess["last_res_id"] = res_id
        sess["last_book_at"] = datetime.now().isoformat(timespec="seconds")
        sess["last_book_sig"] = sig
        name = draft.get("guest_name")
        sess["draft"] = {"guest_name": name} if name else {}
        sess["consult_only"] = False
        sess["whole_dorm_request"] = False
        save_session(sess)
        out["booked"] = True
        out["res_id"] = res_id
        out["payload"] = payload
        out["phase"] = "booked"
        if confirm_token:
            out["confirm_token"] = confirm_token
        _tag(jid, "reservado")
        if pricing.is_shared(payload["room"]):
            out["reply"] = (
                f"¡Listo! Reserva #{res_id} · {payload['guests']} camas en "
                f"{_friendly_room(payload['room']['id'])} · "
                f"{payload['check_in']} al {payload['check_out']} · USD {payload['price_usd']:.0f}. "
                "Si cambia algo, avisame."
            )
        else:
            out["reply"] = (
                f"¡Listo! Reserva #{res_id} · {_friendly_room(payload['room']['id'])} · "
                f"{payload['check_in']} al {payload['check_out']} · USD {payload['price_usd']:.0f}. "
                "Si cambia algo, avisame."
            )
        return out
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        out["reply"] = f"No pude cerrarla ({exc}). Otras fechas?"
        save_session(sess)
        return out


def _missing_es(keys: list[str]) -> str:
    labels = {
        "guests": "cuántas personas",
        "check_in": "fecha de entrada",
        "check_out": "fecha de salida",
        "room_id": "qué habitación",
        "guest_name": "tu nombre",
    }
    return ", ".join(labels.get(k, k) for k in keys)


def _status_line(sess: dict[str, Any]) -> str:
    d = sess.get("draft") or {}
    bits = []
    if d.get("guests"):
        bits.append(f"{d['guests']} pers.")
    if d.get("check_in") and d.get("check_out"):
        bits.append(f"{d['check_in']} al {d['check_out']}")
    if d.get("room_id"):
        bits.append(_friendly_room(str(d["room_id"])))
    return ("Tenemos: " + " · ".join(bits)) if bits else "Decime fechas y personas."
