"""Language detection and short bot strings for WhatsApp (ES/EN/PT)."""
from __future__ import annotations

from collections import defaultdict

_ES_HINTS = (
    "hola", "buenas", "buen dia", "buen día", "gracias", "porfa", "por favor",
    "cuánto", "cuanto", "cuándo", "cuando", "cuántas", "cuantas",
    "habitación", "habitacion", "reservar", "reserva", "disponible",
    "sí", "vos", "che", "tenés", "tenes", "quisiera", "necesito",
)
_EN_HINTS = (
    "hello", "hi ", "hi,", "hey", "please", "thanks", "thank you",
    "room", "price", "how much", "available", "availability", "book",
    "booking", "night", "when", "cost", "check-in", "check in", "checkout",
)
_PT_HINTS = (
    "olá", "ola", "oi ", "oi,", "obrigado", "obrigada", "quarto", "preço",
    "preco", "quanto", "reservar", "disponível", "disponivel", "quando",
    "por favor", "não", "nao", "você", "voce", "gostaria",
)

_STRINGS: dict[str, dict[str, str]] = {
    "es": {
        "greet": "¡Hola{name}! Bienvenido a Valizas Hostel Boutique. ¿Para qué fechas venís?",
        "ask_dates": "Decime las fechas (entrada y salida) y cuántas personas son.",
        "catalog_cooldown": "Ya te pasé las opciones hace un rato — mirá arriba. ¿Alguna te copó?",
        "later_bye": "Dale, quedo atento. ¡Cualquier cosa, escribime!",
        "group_flow": "Para varias habitaciones armamos un combo grupal. Decime cuántas personas en total y las fechas.",
        "unclear": "No te entendí bien. ¿Me contás fechas, personas y si buscás privada o compartida?",
        "consult_only": "Sin problema, esto es solo una cotización — todavía no reserva nada.",
        "combo_10": "Si te quedás {nights}+ noches te hacemos {discount}% off. ¿Seguimos?",
        "whole_dorm_ask": "¿Querés reservar el dormitorio {room} entero (las {beds} camas)?",
        "deposit_line": "Para confirmar pedimos una seña del {pct}% por transferencia; el resto se paga al llegar.",
        "human_handoff": "Ahora te paso con {names} del equipo para que te ayude directamente.",
        "sleep_mode": "Estamos descansando ({start}–{end} hs); apenas se levante el equipo te responden. ¡Gracias por escribir!",
    },
    "en": {
        "greet": "Hi{name}! Welcome to Valizas Hostel Boutique. What dates are you thinking?",
        "ask_dates": "Tell me your check-in and check-out dates, and how many guests.",
        "catalog_cooldown": "I already sent the options a bit ago — scroll up. Did any catch your eye?",
        "later_bye": "Sounds good, I'll be here. Message me whenever!",
        "group_flow": "For multiple rooms we can put together a group combo. Tell me the total guests and dates.",
        "unclear": "Didn't quite catch that. Could you share dates, guest count, and private or shared room?",
        "consult_only": "No worries, this is just a quote — nothing is booked yet.",
        "combo_10": "Stay {nights}+ nights and get {discount}% off. Want to go ahead?",
        "whole_dorm_ask": "Do you want to book the whole {room} dorm (all {beds} beds)?",
        "deposit_line": "To confirm we ask for a {pct}% deposit by transfer; the rest is paid on arrival.",
        "human_handoff": "I'm connecting you with {names} from our team so they can help directly.",
        "sleep_mode": "We're offline right now ({start}-{end}); the team will reply as soon as they're back. Thanks for writing!",
    },
    "pt": {
        "greet": "Oi{name}! Bem-vindo ao Valizas Hostel Boutique. Quais datas você está pensando?",
        "ask_dates": "Me diga as datas de entrada e saída e quantas pessoas são.",
        "catalog_cooldown": "Já te mandei as opções há pouco — dá uma olhada acima. Alguma te agradou?",
        "later_bye": "Combinado, fico por aqui. Qualquer coisa me chama!",
        "group_flow": "Para mais de um quarto montamos um combo em grupo. Me diga o total de pessoas e as datas.",
        "unclear": "Não entendi direito. Pode me dizer as datas, quantas pessoas e se quer privado ou compartilhado?",
        "consult_only": "Sem problema, isso é só uma cotação — ainda não reserva nada.",
        "combo_10": "Ficando {nights}+ noites você ganha {discount}% de desconto. Seguimos?",
        "whole_dorm_ask": "Quer reservar o dormitório {room} inteiro (as {beds} camas)?",
        "deposit_line": "Para confirmar pedimos um sinal de {pct}% por transferência; o resto se paga na chegada.",
        "human_handoff": "Vou te passar para {names} da equipe para te ajudar direto.",
        "sleep_mode": "Estamos fora do horário agora ({start}-{end}); assim que a equipe voltar, respondemos. Obrigado por escrever!",
    },
}


def detect_lang(text: str) -> str:
    """Best-effort keyword-based detection among es/en/pt for a short WhatsApp message."""
    raw = (text or "").lower().strip()
    if not raw:
        return "es"
    lower = f" {raw} "

    es_score = sum(1 for h in _ES_HINTS if h in lower)
    en_score = sum(1 for h in _EN_HINTS if h in lower)
    pt_score = sum(1 for h in _PT_HINTS if h in lower)

    if pt_score > es_score and pt_score > en_score:
        return "pt"
    if en_score > es_score and en_score > pt_score:
        return "en"
    return "es"


def t(lang: str, key: str, **kwargs) -> str:
    """Short bot string for `key` in `lang` (falls back to Spanish)."""
    lang = lang if lang in _STRINGS else "es"
    template = _STRINGS[lang].get(key) or _STRINGS["es"].get(key, "")
    if not template:
        return ""
    safe_kwargs: dict[str, object] = defaultdict(str, **kwargs)
    return template.format_map(safe_kwargs)
