"""Rutas y constantes del escritorio Valizas Reservas."""
from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "Valizas Reservas"
APP_VERSION = "0.4.0"

WHATSAPP_NUMBER = "59894340425"
MAPS_URL = "https://www.google.com/maps/search/?api=1&query=Valizas+Hostel+Boutique"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = BASE_DIR

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "valizas_reservas.db"
ASSETS_DIR = RESOURCE_DIR / "assets"
ASSETS_ROOMS = ASSETS_DIR / "rooms"
SETTINGS_PATH = DATA_DIR / "settings.json"
WA_BRIDGE_DIR = RESOURCE_DIR / "whatsapp-bridge"
WA_AUTH_DIR = DATA_DIR / "wa-auth"
WA_BRIDGE_PORT = 8787

# Brand palette (hostel)
COLORS = {
    "bg": "#0b2a33",
    "surface": "#123a45",
    "surface2": "#1a4a58",
    "accent": "#e07a5f",
    "accent_hover": "#c96850",
    "teal": "#7dcdc0",
    "text": "#f4f0e8",
    "muted": "#b7c2c0",
    "danger": "#e8927a",
    "ok": "#7dcdc0",
    "header": "#0a2430",
}

# Room catalog (capacity + photo stem) — photos from Leo pack
ROOMS = [
    {
        "id": "Hab_priv",
        "name": "Habitación doble privada (baño privado)",
        "capacity": 2,
        "photo": "Hab_priv.webp",
        "kind": "privada",
        "bucket": "suite",
        "blurb": "Doble privada con baño privado.",
    },
    {
        "id": "Hab_Dob",
        "name": "Habitación doble",
        "capacity": 2,
        "photo": "Hab_Dob.webp",
        "kind": "privada",
        "bucket": "suite",
        "blurb": "Doble privada con baño privado.",
    },
    {
        "id": "Hab_Fam",
        "name": "Habitación familiar (sommier + cucheta)",
        "capacity": 4,
        "photo": "Hab_Fam.webp",
        "kind": "privada",
        "bucket": "suite",
        "blurb": "1 sommier 2 plazas + 1 cucheta, baño privado.",
    },
    {
        "id": "Apart_suite_4",
        "name": "Apartamento 4 personas",
        "capacity": 4,
        "photo": "Apart_suite_4.webp",
        "kind": "privada",
        "bucket": "suite",
        "blurb": "Terraza privada, baño privado, smart TV, aire, frigobar y desayuno.",
    },
    {
        "id": "Hab_Priv_2",
        "name": "Doble con vista, balcón y terraza",
        "capacity": 2,
        "photo": "Hab_Priv_2.webp",
        "kind": "privada",
        "bucket": "doble",
        "blurb": "Doble privada, baño compartido, balcón/terraza con vista al mar y la principal.",
    },
    {
        "id": "Hab_Dob_Priv",
        "name": "Doble privada baño compartido",
        "capacity": 2,
        "photo": "Hab_Dob_Priv.webp",
        "kind": "privada",
        "bucket": "doble",
        "blurb": "Doble privada con baño compartido.",
    },
    {
        "id": "Hab_Dob_Priv_2",
        "name": "Doble privada baño compartido II",
        "capacity": 2,
        "photo": "Hab_Dob_Priv_2.webp",
        "kind": "privada",
        "bucket": "doble",
        "blurb": "Doble privada con baño compartido.",
    },
    {
        "id": "Hab_4",
        "name": "Compartida 4 camas (balcón y terraza)",
        "capacity": 4,
        "photo": "Hab_4.webp",
        "kind": "compartida",
        "bucket": "dorm",
        "blurb": "4 camas compartidas con balcón y terraza.",
    },
    {
        "id": "Hab_Comp_6",
        "name": "Compartida 6 camas (balcón y terraza)",
        "capacity": 6,
        "photo": "Hab_Comp_6.webp",
        "kind": "compartida",
        "bucket": "dorm",
        "blurb": "6 camas compartidas con balcón y terraza.",
    },
    {
        "id": "Hab_Comp_8",
        "name": "Compartida 8 camas",
        "capacity": 8,
        "photo": "Hab_Comp_8.webp",
        "kind": "compartida",
        "bucket": "dorm",
        "blurb": "8 camas, lockers, ropa de cama, Wi‑Fi y desayuno.",
    },
]

# Default USD/night ranges by month (from site content)
DEFAULT_RATES = {
    1: {"season": "alta", "suite": (110, 130), "doble": (90, 110), "dorm": (30, 40)},
    2: {"season": "alta", "suite": (105, 125), "doble": (85, 105), "dorm": (28, 38)},
    3: {"season": "media", "suite": (80, 100), "doble": (65, 85), "dorm": (22, 30)},
    4: {"season": "media", "suite": (75, 95), "doble": (60, 80), "dorm": (20, 28)},
    5: {"season": "baja", "suite": (60, 80), "doble": (48, 65), "dorm": (16, 22)},
    6: {"season": "baja", "suite": (58, 78), "doble": (45, 62), "dorm": (15, 21)},
    7: {"season": "media", "suite": (78, 98), "doble": (62, 82), "dorm": (22, 30)},
    8: {"season": "baja", "suite": (60, 80), "doble": (48, 65), "dorm": (16, 22)},
    9: {"season": "baja", "suite": (62, 82), "doble": (50, 68), "dorm": (17, 23)},
    10: {"season": "baja", "suite": (65, 85), "doble": (52, 70), "dorm": (18, 24)},
    11: {"season": "media", "suite": (78, 98), "doble": (62, 82), "dorm": (22, 30)},
    12: {"season": "alta", "suite": (100, 130), "doble": (80, 110), "dorm": (26, 40)},
}

MONTHS_ES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

# Approximate Uruguay coastal season per month, derived from DEFAULT_RATES so
# there is a single source of truth: alta = Dec-Feb, media = Mar-Apr/Jul/Nov,
# baja = the rest.
SEASON_RANGES = [(month, DEFAULT_RATES[month]["season"]) for month in sorted(DEFAULT_RATES)]

DEFAULT_SETTINGS = {
    "ai_provider": "auto",  # auto | groq | gemini | openai | rules
    "groq_api_key": "",
    "groq_model": "llama-3.3-70b-versatile",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "currency": "USD",
    "price_mode": "mid",
    "whatsapp_mode": "live",
    "auto_book": True,  # mensaje entrante → IA → reserva sola
    "auto_book_min_confidence": 0.7,
    "auto_reply": True,  # responder por WhatsApp con Groq
    "pause_all_replies": False,  # interruptor manual de emergencia (Leo)
    "semi_auto": False,  # preparar respuesta pero no enviarla sola (revisar y tocar Enviar)
    "bot_sleep_start": "00:00",  # igual a end = desactivado (el bot responde 24h)
    "bot_sleep_end": "00:00",
    "deposit_pct": 0.3,  # seña para confirmar reserva
    "long_stay_nights": 7,  # a partir de cuántas noches aplica descuento
    "long_stay_discount_pct": 10,
    "child_rate_pct": 50,  # tarifa de niños como % de la tarifa adulto
    "cancellation_policy": "Cancelá gratis hasta 48h antes; después se retiene la seña.",
    "check_in_time": "14:00",
    "check_out_time": "11:00",
    "mixed_dorms": True,  # compartidas mixtas (no separadas por género)
    "upsell_enabled": True,  # sugerir upgrades/combos en la charla
    "catalog_cooldown_sec": 300,  # no repetir el catálogo antes de este tiempo
    "photo_cooldown_sec": 600,  # no repetir la misma foto antes de este tiempo
    "notify_new_messages": True,  # avisar en el escritorio ante mensajes nuevos
    "operator_names": "Leo, Rubén",  # a quién se deriva un handoff humano
}

# Preguntas frecuentes cortas para responder por WhatsApp (español rioplatense).
HOSTEL_FAQ = {
    "checkin": "El check-in es a partir de las 14:00. Si llegás antes, te guardamos el equipaje.",
    "checkout": "El check-out es hasta las 11:00. Si tu ómnibus sale más tarde, te guardamos el equipaje.",
    "parking": "Sí, hay lugar para estacionar dentro del predio, sin cargo.",
    "pool": "No tenemos piscina, pero estamos a pocas cuadras del mar y de la laguna.",
    "breakfast": "El desayuno está incluido en todas las habitaciones.",
    "pets": "Por ahora no aceptamos mascotas, salvo que consultes antes por un caso puntual.",
    "location": f"Estamos en Valizas, Rocha. Ubicación: {MAPS_URL}",
    "wifi": "Sí, Wi‑Fi gratis en toda la casa.",
    "lockers": "Las habitaciones compartidas tienen lockers individuales.",
    "payment": "Aceptamos efectivo (UYU/USD) y transferencia. La seña reserva el lugar.",
    "deposit": "Para confirmar pedimos una seña del 30% del total; el resto se paga al llegar.",
    "cancellation": "Cancelá gratis hasta 48h antes; después se retiene la seña.",
    "towels": "Sí, incluimos ropa de cama y toallas.",
    "kitchen": "Tenemos cocina compartida para uso de los huéspedes.",
}

HOSTEL_FAQ_EN = {
    "checkin": "Check-in starts at 2:00 PM. Early arrivals can leave their luggage with us.",
    "checkout": "Check-out is by 11:00 AM. We can store your bags if your bus leaves later.",
    "parking": "Yes, free parking is available on site.",
    "pool": "No pool, but we're a short walk from the beach and the lagoon.",
    "breakfast": "Breakfast is included with every room.",
    "pets": "We don't usually accept pets — message us if you have a special case.",
    "location": f"We're in Valizas, Rocha, Uruguay. Map: {MAPS_URL}",
    "wifi": "Yes, free Wi‑Fi throughout the hostel.",
    "lockers": "Dorm rooms include individual lockers.",
    "payment": "We accept cash (UYU/USD) and bank transfer. A deposit secures your booking.",
    "deposit": "We ask for a 30% deposit to confirm; the rest is paid on arrival.",
    "cancellation": "Free cancellation up to 48h before arrival; the deposit is kept after that.",
    "towels": "Bed linens and towels are included.",
    "kitchen": "We have a shared kitchen for guest use.",
}

HOSTEL_FAQ_PT = {
    "checkin": "O check-in é a partir das 14h. Se chegar antes, podemos guardar sua bagagem.",
    "checkout": "O check-out é até às 11h. Se o ônibus sair mais tarde, guardamos sua bagagem.",
    "parking": "Sim, temos estacionamento gratuito no local.",
    "pool": "Não temos piscina, mas ficamos a poucas quadras do mar e da lagoa.",
    "breakfast": "O café da manhã está incluído em todos os quartos.",
    "pets": "Por enquanto não aceitamos animais, salvo consulta prévia.",
    "location": f"Estamos em Valizas, Rocha, Uruguai. Mapa: {MAPS_URL}",
    "wifi": "Sim, Wi‑Fi grátis em toda a casa.",
    "lockers": "Os quartos compartilhados têm lockers individuais.",
    "payment": "Aceitamos dinheiro (UYU/USD) e transferência. O sinal garante a reserva.",
    "deposit": "Pedimos um sinal de 30% para confirmar; o resto se paga na chegada.",
    "cancellation": "Cancelamento grátis até 48h antes; depois disso o sinal fica retido.",
    "towels": "Incluímos roupa de cama e toalhas.",
    "kitchen": "Temos cozinha compartilhada para os hóspedes.",
}
