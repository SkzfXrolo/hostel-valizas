"""Extract reservation fields from WhatsApp text (rules + free AI: Groq/Gemini)."""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, timedelta
from typing import Any

from . import dates_smart, db
from .config import ROOMS
from .pricing import parse_date

# Room aliases used both to *find* a room mentioned in free text (rules
# extraction) and to *validate* that an AI-proposed room_id is actually
# grounded in the guest's own words (never trust the model to invent one).
ROOM_ALIASES: list[tuple[str, list[str]]] = [
    ("Apart_suite_4", ["apart suite", "apartamento", "apart"]),
    ("Hab_Fam", ["familiar", "familia", "sommier", "cucheta"]),
    ("Hab_priv", ["baño privado en suite", "baño en suite", "suite"]),
    ("Hab_Dob", ["doble con baño", "doble suite"]),
    ("Hab_Priv_2", ["vista al mar", "vista mar", "terraza con vista"]),
    ("Hab_Dob_Priv", ["baño compartido", "doble privada"]),
    ("Hab_Dob_Priv_2", ["doble baño compartido"]),
    ("Hab_Comp_8", ["dorm 8", "dormitorio 8", "8 camas", "compartida 8"]),
    ("Hab_Comp_6", ["dorm 6", "dormitorio 6", "6 camas", "compartida 6"]),
    ("Hab_4", ["dorm 4", "dormitorio 4", "4 camas", "compartida 4"]),
]

# Generic hints (not tied to one room) that the guest *did* mention some kind
# of room, used as a looser fallback so we don't strip a legitimate pick that
# doesn't match the exact alias list above (e.g. "doble", "compartida").
_ROOM_GENERIC_HINTS = (
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
)

MONTH_MAP = {
    "enero": 1,
    "ene": 1,
    "february": 2,
    "febrero": 2,
    "feb": 2,
    "marzo": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "mayo": 5,
    "may": 5,
    "junio": 6,
    "jun": 6,
    "julio": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "septiembre": 9,
    "sep": 9,
    "setiembre": 9,
    "octubre": 10,
    "oct": 10,
    "noviembre": 11,
    "nov": 11,
    "diciembre": 12,
    "dic": 12,
}


def _year_guess(month: int) -> int:
    today = date.today()
    year = today.year
    if month < today.month - 1:
        year += 1
    return year


def _parse_spanish_date(token: str, default_year: int | None = None) -> date | None:
    token = token.strip().lower().replace(" de ", " ")
    m = re.match(r"^(\d{1,2})\s+([a-záéíóú]+)$", token)
    if m:
        day = int(m.group(1))
        month = MONTH_MAP.get(m.group(2))
        if not month:
            return None
        year = default_year or _year_guess(month)
        try:
            return date(year, month, day)
        except ValueError:
            return None
    try:
        return parse_date(token)
    except ValueError:
        return None


def extract_with_rules(text: str) -> dict[str, Any]:
    raw = text.strip()
    lower = raw.lower()
    result: dict[str, Any] = {
        "guest_name": None,
        "guests": None,
        "room_id": None,
        "check_in": None,
        "check_out": None,
        "confidence": 0.4,
        "notes": raw[:500],
        "engine": "rules",
    }

    g = re.search(r"(\d+)\s*(personas?|pax|gente|hu[eé]spedes?)", lower)
    if g:
        result["guests"] = int(g.group(1))
    else:
        g2 = re.search(r"somos\s+(\d+)", lower)
        if g2:
            result["guests"] = int(g2.group(1))

    n = re.search(
        r"(?i)(?:soy|me llamo|nombre\s*[:=]\s*)\s*([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ]+){0,2})",
        raw,
    )
    stop_words = {"somos", "quiero", "queremos", "busco", "buscamos", "necesito", "para", "del", "con"}
    if n:
        parts = [p for p in n.group(1).strip().split() if p.lower() not in stop_words]
        if parts:
            result["guest_name"] = " ".join(parts)
    if not result["guest_name"]:
        n2 = re.search(r"(?i)hola[!,\s]+soy\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]+)", raw)
        if n2 and n2.group(1).lower() not in stop_words:
            result["guest_name"] = n2.group(1).strip().title()

    for room_id, aliases in ROOM_ALIASES:
        if any(a in lower for a in aliases):
            result["room_id"] = room_id
            break
    if result["room_id"] is None and "dorm" in lower:
        guests = result["guests"] or 1
        for room in sorted(ROOMS, key=lambda r: r["capacity"]):
            if room["kind"] == "compartida" and room["capacity"] >= guests:
                result["room_id"] = room["id"]
                break

    range_patterns = [
        r"del?\s+(\d{1,2})\s+al?\s+(\d{1,2})\s+(?:de\s+)?([a-záéíóú]+)",
        r"del?\s+(\d{1,2}\s+(?:de\s+)?[a-záéíóú]+)\s+al?\s+(\d{1,2}\s+(?:de\s+)?[a-záéíóú]+)",
        r"del?\s+(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s+al?\s+(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",
        r"(\d{4}-\d{2}-\d{2})\s*(?:al?|a|→|->)\s*(\d{4}-\d{2}-\d{2})",
        r"(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:al?|a)\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    ]
    for idx, pat in enumerate(range_patterns):
        m = re.search(pat, lower)
        if not m:
            continue
        if idx == 0:
            month = MONTH_MAP.get(m.group(3))
            if not month:
                continue
            year = _year_guess(month)
            try:
                d1 = date(year, month, int(m.group(1)))
                d2 = date(year, month, int(m.group(2)))
            except ValueError:
                continue
        else:
            d1 = _parse_spanish_date(m.group(1))
            d2 = _parse_spanish_date(m.group(2))
            if not d1 or not d2:
                continue
        result["check_in"] = d1.isoformat()
        result["check_out"] = d2.isoformat()
        break

    if not result["check_out"] and result["check_in"]:
        nites = re.search(r"(\d+)\s*noches?", lower)
        if nites:
            cin = date.fromisoformat(result["check_in"])
            result["check_out"] = (cin + timedelta(days=int(nites.group(1)))).isoformat()

    filled = sum(1 for k in ("guest_name", "guests", "room_id", "check_in", "check_out") if result.get(k))
    result["confidence"] = round(0.35 + filled * 0.12, 2)
    return result


def _extraction_prompt(text: str) -> str:
    room_ids = ", ".join(r["id"] for r in ROOMS)
    today = date.today().isoformat()
    return f"""Extraé datos de una consulta de reserva de hostel en Uruguay.
Hoy es {today}.
Devolvé SOLO JSON con claves:
guest_name (string|null), guests (int|null), room_id (uno de: {room_ids} o null),
check_in (YYYY-MM-DD|null), check_out (YYYY-MM-DD|null), notes (string).
Reglas estrictas (NUNCA las rompas):
- NUNCA inventes ni asumas un room_id: solo poné uno si el huésped lo nombró
  explícitamente (tipo de habitación, cantidad de camas, "suite", "apart", etc.).
  Si tenés dudas, dejalo en null.
- NUNCA inventes precios ni disponibilidad; esta extracción no calcula precio.
- check_out es el día que se van (no duermen esa noche).
- Si piden dormitorio y dan cantidad de personas, elegí el dorm más chico que entre
  SOLO si mencionaron "dormitorio"/"compartida"; si no, dejalo null.
- No inventes nombre si no está.
Mensaje:
\"\"\"{text}\"\"\""""


def _room_mentioned_in_text(text: str, room_id: str | None) -> bool:
    """True if the guest's own words justify `room_id` (never trust the model blindly)."""
    if not room_id:
        return False
    lower = (text or "").lower()
    for rid, aliases in ROOM_ALIASES:
        if rid == room_id and any(a in lower for a in aliases):
            return True
    return any(h in lower for h in _ROOM_GENERIC_HINTS)


def _dates_smart_hook(text: str, result: dict[str, Any]) -> dict[str, Any]:
    """Prefer deterministic date rules over AI guesses for relative phrases.

    Phrases like "este finde", "puente" or "la noche del 10" are exact,
    computable facts; letting an LLM guess them risks a wrong year/day, so
    when `dates_smart` can resolve a date we override whatever the AI/rules
    path produced.
    """
    try:
        ci, co = dates_smart.parse_relative_dates(text)
        if not ci:
            ci, co = dates_smart.parse_noche_del(text)
        hint_in = None
        if result.get("check_in"):
            try:
                hint_in = date.fromisoformat(str(result["check_in"]))
            except ValueError:
                hint_in = None
        if ci and not co:
            _, co2 = dates_smart.parse_salgo_el(text, check_in_hint=ci)
            co = co2 or co
        elif not ci:
            ci2, co2 = dates_smart.parse_salgo_el(text, check_in_hint=hint_in)
            if co2:
                ci, co = ci2, co2
        if ci:
            result["check_in"] = ci.isoformat()
        if co:
            result["check_out"] = co.isoformat()
    except Exception:  # noqa: BLE001
        pass
    return result


def _merge_with_rules(data: dict[str, Any], text: str, engine: str) -> dict[str, Any]:
    rules = extract_with_rules(text)
    for key in ("guest_name", "guests", "room_id", "check_in", "check_out"):
        if data.get(key) in (None, "", 0):
            data[key] = rules.get(key)
    if data.get("room_id") and not _room_mentioned_in_text(text, data.get("room_id")):
        # The model proposed a room the guest never actually named — drop it.
        data["room_id"] = None
    data["notes"] = data.get("notes") or rules.get("notes")
    data["engine"] = engine
    data["confidence"] = data.get("confidence") or 0.85
    return _dates_smart_hook(text, data)


def extract_with_openai_compatible(
    text: str,
    api_key: str,
    model: str,
    base_url: str,
    engine_name: str,
) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Sos un extractor de reservas. Respondé JSON válido."},
            {"role": "user", "content": _extraction_prompt(text)},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    return _merge_with_rules(data, text, engine_name)


def extract_with_groq(text: str, api_key: str, model: str) -> dict[str, Any]:
    return extract_with_openai_compatible(
        text,
        api_key,
        model,
        "https://api.groq.com/openai/v1",
        f"groq:{model}",
    )


def extract_with_openai(text: str, api_key: str, model: str = "gpt-4o-mini") -> dict[str, Any]:
    return extract_with_openai_compatible(
        text,
        api_key,
        model,
        "https://api.openai.com/v1",
        "openai",
    )


def extract_with_gemini(text: str, api_key: str, model: str = "gemini-2.0-flash") -> dict[str, Any]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )
    body = {
        "contents": [{"parts": [{"text": _extraction_prompt(text)}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    raw = payload["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(raw)
    return _merge_with_rules(data, text, f"gemini:{model}")


def _try_provider(name: str, text: str, settings: dict[str, Any]) -> dict[str, Any] | None:
    try:
        if name == "groq":
            key = (settings.get("groq_api_key") or "").strip()
            if not key:
                return None
            return extract_with_groq(text, key, settings.get("groq_model", "llama-3.3-70b-versatile"))
        if name == "gemini":
            key = (settings.get("gemini_api_key") or "").strip()
            if not key:
                return None
            return extract_with_gemini(text, key, settings.get("gemini_model", "gemini-2.0-flash"))
        if name == "openai":
            key = (settings.get("openai_api_key") or "").strip()
            if not key:
                return None
            return extract_with_openai(text, key, settings.get("openai_model", "gpt-4o-mini"))
        if name == "rules":
            return extract_with_rules(text)
    except Exception as exc:  # noqa: BLE001
        fallback = extract_with_rules(text)
        fallback["engine"] = f"rules(fallback:{name}:{exc.__class__.__name__})"
        return fallback
    return None


def _extract_reservation_impl(text: str) -> dict[str, Any]:
    settings = db.load_settings()
    provider = (settings.get("ai_provider") or "auto").strip().lower()

    if provider == "rules":
        return extract_with_rules(text)

    if provider in ("groq", "gemini", "openai"):
        result = _try_provider(provider, text, settings)
        return result or extract_with_rules(text)

    # auto: prefer free tiers first
    for name in ("groq", "gemini", "openai"):
        result = _try_provider(name, text, settings)
        if result and not str(result.get("engine", "")).startswith("rules(fallback"):
            return result
        if result and result.get("engine", "").startswith("rules(fallback"):
            # keep last fallback but continue trying other providers
            continue
    return extract_with_rules(text)


def extract_reservation(text: str) -> dict[str, Any]:
    """Public entry point: extract + guarantee an `engine` tag + deterministic dates.

    The `engine` field is always present (rules/groq:<model>/gemini:<model>/
    openai/rules(fallback:...)) so every message can be audited later, and
    `dates_smart` gets one last say over relative date phrases regardless of
    which extraction path produced the result (see `_dates_smart_hook`).
    """
    result = _extract_reservation_impl(text)
    result.setdefault("engine", "rules")
    if not result.get("engine"):
        result["engine"] = "rules"
    return _dates_smart_hook(text, result)


_MISSING_LABELS = {
    "guests": "cuántas personas vienen",
    "room_id": "si prefieren suite, doble, familiar, apart o dormitorio",
    "check_in": "fecha de entrada",
    "check_out": "fecha de salida",
    "guest_name": "nombre",
}


def _chat_completion(system: str, user: str, settings: dict[str, Any] | None = None) -> str | None:
    settings = settings or db.load_settings()
    groq_key = (settings.get("groq_api_key") or "").strip()
    if groq_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            resp = client.chat.completions.create(
                model=settings.get("groq_model", "llama-3.3-70b-versatile"),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.55,
                max_tokens=280,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text or None
        except Exception:  # noqa: BLE001
            pass

    gemini_key = (settings.get("gemini_api_key") or "").strip()
    if gemini_key:
        try:
            model = settings.get("gemini_model", "gemini-2.0-flash")
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                f"?key={gemini_key}"
            )
            body = {
                "contents": [{"parts": [{"text": f"{system}\n\n{user}"}]}],
                "generationConfig": {"temperature": 0.55, "maxOutputTokens": 280},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return (payload["candidates"][0]["content"]["parts"][0]["text"] or "").strip() or None
        except Exception:  # noqa: BLE001
            pass
    return None


def craft_whatsapp_reply(
    *,
    kind: str,
    guest_message: str,
    from_name: str = "",
    parsed: dict[str, Any] | None = None,
    missing: list[str] | None = None,
    error: str | None = None,
    payload: dict[str, Any] | None = None,
    res_id: int | None = None,
) -> str:
    """Respuesta cálida estilo Valizas Hostel (Groq primero, plantilla si no hay key)."""
    parsed = parsed or {}
    missing = missing or []
    name = from_name or parsed.get("guest_name") or ""

    system = (
        "Sos el anfitrión de Valizas Hostel (Valizas, Rocha, Uruguay), con Leonardo y Rubén. "
        "Escribís por WhatsApp: cálido, claro, breve, en español rioplatense. "
        "Sin emojis excesivos (máx 1). "
        "REGLAS ESTRICTAS, nunca las rompas: "
        "1) NUNCA inventes precios — usá SOLO el monto en USD que te paso en el mensaje, "
        "si no te paso ninguno no menciones ningún número. "
        "2) NUNCA inventes ni menciones códigos de habitación (como Hab_Comp_8, Hab_Dob, etc.); "
        "usá nombres simples (\"la doble\", \"la compartida de 8\"). "
        "3) NUNCA inventes disponibilidad ni fechas que no te haya dado el huésped o el sistema. "
        "4) Si tenés dudas o falta un dato, respondé en máximo 2 líneas pidiendo solo eso. "
        "5) Usá SOLO los hechos que te paso abajo; no completes con información propia. "
        "No firmes con 'IA'. Suená humano y hospitalario."
    )

    if kind == "ask_missing":
        need = ", ".join(_MISSING_LABELS.get(m, m) for m in missing) or "algunos datos"
        known = []
        if parsed.get("guest_name"):
            known.append(f"nombre: {parsed['guest_name']}")
        if parsed.get("guests"):
            known.append(f"personas: {parsed['guests']}")
        if parsed.get("room_id"):
            known.append(f"habitación: {parsed['room_id']}")
        if parsed.get("check_in"):
            known.append(f"entrada: {parsed['check_in']}")
        if parsed.get("check_out"):
            known.append(f"salida: {parsed['check_out']}")
        known_txt = " | ".join(known) if known else "casi nada"
        user = (
            "Un huésped escribió:\n"
            f'"""{guest_message}"""\n'
            f"Nombre de contacto WhatsApp: {name or 'desconocido'}.\n"
            f"Ya entendimos: {known_txt}.\n"
            f"Falta pedir amablemente: {need}.\n"
            "Pedí solo lo que falta, invitá a responder en un solo mensaje, y agradecé. "
            "Máximo 2 líneas."
        )
        ai = _chat_completion(system, user)
        if ai:
            return ai
        ask = ", ".join(_MISSING_LABELS.get(m, m) for m in missing)
        hello = f"Hola {name}!" if name else "Hola!"
        return (
            f"{hello} Gracias por escribir a Valizas Hostel 🌿\n"
            f"Para armarte la reserva necesito: {ask}.\n"
            "¿Me lo pasás en un solo mensaje?"
        )

    if kind == "booked":
        room_name = (payload or {}).get("room", {}).get("name") or parsed.get("room_id") or "habitación"
        guests = (payload or {}).get("guests") or parsed.get("guests")
        cin = (payload or {}).get("check_in") or parsed.get("check_in")
        cout = (payload or {}).get("check_out") or parsed.get("check_out")
        price = (payload or {}).get("price_usd")
        user = (
            "Confirmá una reserva ya cargada.\n"
            f"Huésped: {name or 'huésped'}\n"
            f"Reserva #{res_id}\n"
            f"{room_name}, {guests} personas, {cin} → {cout}\n"
            f"Total USD {price}\n"
            "Mensaje original del huésped:\n"
            f'"""{guest_message}"""\n'
            "Confirmá con calidez, mencioná que quedó anotada y que cualquier cambio nos escriban. "
            "Máximo 4 líneas. Usá el precio y la habitación EXACTAMENTE como te los pasé, no los cambies."
        )
        ai = _chat_completion(system, user)
        if ai:
            return ai
        hello = f"¡Listo {name}!" if name else "¡Listo!"
        return (
            f"{hello} Quedó reservado en Valizas Hostel 🌿\n"
            f"#{res_id} · {room_name} · {guests} pers.\n"
            f"{cin} → {cout} · USD {(price or 0):.0f}\n"
            "Si necesitás cambiar algo, escribinos."
        )

    # error / unavailable
    user = (
        "No pudimos completar la reserva.\n"
        f"Motivo técnico: {error or 'sin detalle'}\n"
        f"Datos entendidos: {json.dumps(parsed, ensure_ascii=False)}\n"
        "Mensaje del huésped:\n"
        f'"""{guest_message}"""\n'
        "Explicá con amabilidad qué pasó y pedí una alternativa (otras fechas o tipo de habitación). "
        "Máximo 2 líneas. No inventes ninguna fecha ni precio alternativo."
    )
    ai = _chat_completion(system, user)
    if ai:
        return ai
    hello = f"Hola {name}!" if name else "Hola!"
    return (
        f"{hello} Gracias por escribir.\n"
        f"No pudimos cerrar la reserva así: {error or 'faltan datos o no hay disponibilidad'}.\n"
        "¿Probamos con otras fechas o tipo de habitación?"
    )
