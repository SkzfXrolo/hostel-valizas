"""Booking voucher generator.

`reportlab` isn't in requirements.txt, so this writes a clean, print-ready
HTML voucher (any browser can "Print → Save as PDF") plus a plain-text copy
for quick WhatsApp/email pasting. If `reportlab` ever gets added to
requirements, this module will automatically prefer it and emit a real PDF.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .config import APP_NAME, MAPS_URL, WHATSAPP_NUMBER

try:
    import reportlab  # noqa: F401

    HAVE_REPORTLAB = True
except ImportError:
    HAVE_REPORTLAB = False


def _fmt_money(value: Any) -> str:
    try:
        return f"USD {float(value):.0f}"
    except (TypeError, ValueError):
        return "—"


def _room_name(reservation: dict[str, Any]) -> str:
    room = reservation.get("room")
    if isinstance(room, dict) and room.get("name"):
        return str(room["name"])
    return str(reservation.get("room_name") or reservation.get("room_id") or "Habitación")


def _safe_slug(text: str) -> str:
    slug = "".join(c if c.isalnum() else "_" for c in text.strip())
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "huesped"


def _voucher_stem(reservation: dict[str, Any]) -> str:
    rid = reservation.get("id") or reservation.get("res_id") or "sinid"
    slug = _safe_slug(str(reservation.get("guest_name") or "huesped"))
    return f"voucher_{rid}_{slug}"


def _fields(reservation: dict[str, Any]) -> dict[str, str]:
    guests = reservation.get("guests")
    adults = reservation.get("adults")
    children = reservation.get("children") or 0
    guests_line = f"{guests} personas" if guests else "—"
    if adults and children:
        guests_line = f"{adults} adultos + {children} niños"
    return {
        "app_name": APP_NAME,
        "res_id": str(reservation.get("id") or reservation.get("res_id") or "—"),
        "guest_name": str(reservation.get("guest_name") or "—"),
        "room_name": _room_name(reservation),
        "check_in": str(reservation.get("check_in") or "—"),
        "check_out": str(reservation.get("check_out") or "—"),
        "nights": str(reservation.get("nights") or "—"),
        "guests_line": guests_line,
        "price": _fmt_money(reservation.get("price_usd")),
        "deposit": _fmt_money(reservation.get("deposit_usd")) if reservation.get("deposit_usd") else "—",
        "status": str(reservation.get("status") or "confirmed"),
        "whatsapp": str(reservation.get("whatsapp") or "—"),
        "notes": str(reservation.get("notes") or ""),
        "issued_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "maps_url": MAPS_URL,
        "hostel_whatsapp": WHATSAPP_NUMBER,
    }


def render_voucher_text(reservation: dict[str, Any]) -> str:
    f = _fields(reservation)
    lines = [
        f"{f['app_name']} — Voucher de reserva #{f['res_id']}",
        "=" * 44,
        f"Huésped: {f['guest_name']}",
        f"Habitación: {f['room_name']}",
        f"Check-in: {f['check_in']}  ·  Check-out: {f['check_out']}  ·  {f['nights']} noches",
        f"Huéspedes: {f['guests_line']}",
        f"Total: {f['price']}" + (f"  ·  Seña: {f['deposit']}" if f["deposit"] != "—" else ""),
        f"Estado: {f['status']}",
    ]
    if f["notes"]:
        lines.append(f"Notas: {f['notes']}")
    lines.append("")
    lines.append(f"Ubicación: {f['maps_url']}")
    lines.append(f"Consultas: WhatsApp +{f['hostel_whatsapp']}")
    lines.append(f"Emitido: {f['issued_at']}")
    return "\n".join(lines) + "\n"


def render_voucher_html(reservation: dict[str, Any]) -> str:
    f = _fields(reservation)
    notes_html = f"<p class='notes'><strong>Notas:</strong> {f['notes']}</p>" if f["notes"] else ""
    deposit_html = f" · Seña: <strong>{f['deposit']}</strong>" if f["deposit"] != "—" else ""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>Voucher #{f['res_id']} — {f['app_name']}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; background: #f4f0e8; color: #123a45;
         margin: 0; padding: 32px; }}
  .card {{ max-width: 620px; margin: 0 auto; background: #fff; border-radius: 14px;
           padding: 32px 40px; box-shadow: 0 6px 24px rgba(10, 36, 48, 0.15); }}
  h1 {{ font-size: 22px; margin: 0 0 4px; color: #0a2430; }}
  .sub {{ color: #7a8b89; margin: 0 0 24px; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 8px 0; border-bottom: 1px solid #eee; font-size: 14px; vertical-align: top; }}
  td.label {{ color: #7a8b89; width: 40%; }}
  .price {{ font-size: 20px; font-weight: bold; color: #c96850; }}
  .notes {{ margin-top: 18px; font-size: 13px; color: #444; }}
  .footer {{ margin-top: 28px; font-size: 12px; color: #7a8b89; border-top: 1px dashed #ddd; padding-top: 14px; }}
  .status {{ display: inline-block; padding: 2px 10px; border-radius: 999px; background: #e6f4f1;
             color: #146b57; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
  @media print {{ body {{ background: #fff; padding: 0; }} .card {{ box-shadow: none; }} }}
</style>
</head>
<body>
  <div class="card">
    <h1>{f['app_name']} · Voucher de reserva #{f['res_id']}</h1>
    <p class="sub">Emitido {f['issued_at']} · <span class="status">{f['status']}</span></p>
    <table>
      <tr><td class="label">Huésped</td><td>{f['guest_name']}</td></tr>
      <tr><td class="label">Habitación</td><td>{f['room_name']}</td></tr>
      <tr><td class="label">Check-in</td><td>{f['check_in']} (desde 14:00)</td></tr>
      <tr><td class="label">Check-out</td><td>{f['check_out']} (hasta 11:00)</td></tr>
      <tr><td class="label">Noches</td><td>{f['nights']}</td></tr>
      <tr><td class="label">Huéspedes</td><td>{f['guests_line']}</td></tr>
      <tr><td class="label">Total</td><td class="price">{f['price']}{deposit_html}</td></tr>
    </table>
    {notes_html}
    <div class="footer">
      Ubicación: <a href="{f['maps_url']}">{f['maps_url']}</a><br />
      Consultas: WhatsApp +{f['hostel_whatsapp']}
    </div>
  </div>
</body>
</html>
"""


def _write_pdf_reportlab(reservation: dict[str, Any], path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    f = _fields(reservation)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, _height = A4
    y = 270 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, f"{f['app_name']} — Voucher #{f['res_id']}")
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    rows = [
        ("Huésped", f["guest_name"]),
        ("Habitación", f["room_name"]),
        ("Check-in", f["check_in"]),
        ("Check-out", f["check_out"]),
        ("Noches", f["nights"]),
        ("Huéspedes", f["guests_line"]),
        ("Total", f["price"]),
        ("Seña", f["deposit"]),
        ("Estado", f["status"]),
    ]
    for label, value in rows:
        c.drawString(20 * mm, y, f"{label}: {value}")
        y -= 7 * mm
    if f["notes"]:
        c.drawString(20 * mm, y, f"Notas: {f['notes'][:90]}")
        y -= 7 * mm
    y -= 5 * mm
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(20 * mm, y, f"Ubicación: {f['maps_url']}")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"Consultas: WhatsApp +{f['hostel_whatsapp']}")
    c.showPage()
    c.save()


def save_voucher(reservation: dict[str, Any], dest_dir: Path | str) -> Path:
    """Write a voucher for `reservation` under `dest_dir` and return its path.

    `reservation` accepts either a DB row-style dict (room_name, guests, ...)
    or a `pricing.validate_booking` payload (nested "room": {...}). Writes a
    PDF if reportlab is available, otherwise an HTML file (print-ready) plus
    a plain-text sibling for quick copy/paste.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = _voucher_stem(reservation)

    if HAVE_REPORTLAB:
        path = dest_dir / f"{stem}.pdf"
        _write_pdf_reportlab(reservation, path)
        return path

    html_path = dest_dir / f"{stem}.html"
    html_path.write_text(render_voucher_html(reservation), encoding="utf-8")
    txt_path = dest_dir / f"{stem}.txt"
    txt_path.write_text(render_voucher_text(reservation), encoding="utf-8")
    return html_path
