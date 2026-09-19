"""Valizas Reservas — desktop UI (marca + WhatsApp live + IA gratuita)."""
from __future__ import annotations

import base64
import calendar
import io
import subprocess
import sys
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

import customtkinter as ctk
from PIL import Image, ImageEnhance, ImageFilter
from tkinter import messagebox

from . import ai_parser, db, pricing
from .config import (
    APP_NAME,
    APP_VERSION,
    ASSETS_DIR,
    ASSETS_ROOMS,
    COLORS,
    DATA_DIR,
    MONTHS_ES,
)
from .wa_client import WhatsAppBridge
from . import wa_flow

try:
    from . import media_util
except Exception:  # noqa: BLE001
    media_util = None  # type: ignore[assignment]


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


def _send_windows_notification(title: str, message: str) -> None:
    """Best-effort desktop notification for new WhatsApp messages.

    Tries win10toast, then plyer, then a PowerShell balloon-tip fallback on
    Windows. Never raises — silently no-ops if nothing is available.
    """
    title = (title or "")[:60]
    message = (message or "")[:180]
    try:
        from win10toast import ToastNotifier  # type: ignore

        ToastNotifier().show_toast(title, message, duration=5, threaded=True)
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        from plyer import notification  # type: ignore

        notification.notify(title=title, message=message, timeout=5)
        return
    except Exception:  # noqa: BLE001
        pass
    if sys.platform != "win32":
        return
    try:
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")
        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "Add-Type -AssemblyName System.Drawing;"
            "$n = New-Object System.Windows.Forms.NotifyIcon;"
            "$n.Icon = [System.Drawing.SystemIcons]::Information;"
            "$n.Visible = $true;"
            f"$n.ShowBalloonTip(5000, '{safe_title}', '{safe_message}', "
            "[System.Windows.Forms.ToolTipIcon]::Info);"
            "Start-Sleep -Seconds 6;"
            "$n.Dispose();"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:  # noqa: BLE001
        pass


class ValizasApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        db.init_db()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x820")
        self.minsize(1080, 720)
        self.configure(fg_color=COLORS["bg"])

        self._photo_refs: list[Any] = []
        self.cal_year = date.today().year
        self.cal_month = date.today().month
        self._inbox_parsed: dict | None = None
        self._wa = WhatsAppBridge()
        self._wa.on_update = self._on_wa_status
        self._wa_last_msg_id = 0
        self._wa_messages: list[dict] = []
        self._wa_processed_ids: set[int] = set()
        self._bg_label: ctk.CTkLabel | None = None
        self._auto_busy = False

        self._build_background()
        self._build_header()

        self.tabs = ctk.CTkTabview(
            self,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface2"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["surface2"],
            text_color=COLORS["text"],
        )
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.tab_wa = self.tabs.add("1 · WhatsApp")
        self.tab_new = self.tabs.add("2 · Nueva reserva")
        self.tab_cal = self.tabs.add("3 · Calendario")
        self.tab_rates = self.tabs.add("4 · Tarifas")
        self.tab_ops = self.tabs.add("5 · Operador")
        self.tab_cfg = self.tabs.add("6 · Config / IA")

        self._build_whatsapp()
        self._build_new()
        self._build_calendar()
        self._build_rates()
        self._build_ops()
        self._build_config()
        self.refresh_calendar()
        self.refresh_rates()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # —— visuals ——
    def _load_image(self, path, size=None, darken: float = 1.0):
        if not path.exists():
            return None
        img = Image.open(path).convert("RGB")
        if darken < 1.0:
            img = ImageEnhance.Brightness(img).enhance(darken)
            img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
        if size:
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
        else:
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img)
        self._photo_refs.append(ctk_img)
        return ctk_img

    def _build_background(self) -> None:
        bg_path = ASSETS_DIR / "bg-hero.webp"
        if not bg_path.exists():
            return
        # soft full-window atmosphere
        w, h = 1280, 820
        img = Image.open(bg_path).convert("RGB").resize((w, h))
        img = ImageEnhance.Brightness(img).enhance(0.28)
        img = ImageEnhance.Color(img).enhance(0.75)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
        self._photo_refs.append(ctk_img)
        self._bg_label = ctk.CTkLabel(self, text="", image=ctk_img)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._bg_label.lower()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLORS["header"], corner_radius=0, height=78)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo = self._load_image(ASSETS_DIR / "logo.webp", size=(210, 52))
        if logo:
            ctk.CTkLabel(header, text="", image=logo).pack(side="left", padx=(18, 10), pady=10)
        else:
            ctk.CTkLabel(
                header,
                text="Valizas Hostel",
                font=ctk.CTkFont(family="Georgia", size=26, weight="bold"),
                text_color=COLORS["text"],
            ).pack(side="left", padx=20)

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.pack(side="left", fill="y", pady=12)
        ctk.CTkLabel(
            titles,
            text="Reservas",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles,
            text="WhatsApp en vivo · calendario · tarifas · IA gratuita",
            text_color=COLORS["muted"],
            anchor="w",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w")

        header_right = ctk.CTkFrame(header, fg_color="transparent")
        header_right.pack(side="right", fill="y", padx=20, pady=8)

        top_row = ctk.CTkFrame(header_right, fg_color="transparent")
        top_row.pack(anchor="e")
        ctk.CTkLabel(
            top_row,
            text=f"v{APP_VERSION}",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 10))
        self.header_wa = ctk.CTkLabel(
            top_row,
            text="WhatsApp: desconectado",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=13),
        )
        self.header_wa.pack(side="left")

        self.header_pause_btn = ctk.CTkButton(
            header_right,
            text="⏸ Pausar respuestas automáticas",
            width=250,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.toggle_pause_all,
        )
        self.header_pause_btn.pack(anchor="e", pady=(6, 0))
        self._refresh_pause_button()

    def room_photo(self, room_id: str, size=(420, 260)):
        room = db.get_room(room_id)
        path = ASSETS_ROOMS / (room["photo"] if room else "rooms-generic.webp")
        if not path.exists():
            path = ASSETS_ROOMS / "rooms-generic.webp"
        return self._load_image(path, size=size)

    def set_status(self, widget: ctk.CTkLabel, text: str, ok: bool = True) -> None:
        widget.configure(text=text, text_color=COLORS["ok"] if ok else COLORS["danger"])

    # —— pausa global (humano al mando) ——
    def toggle_pause_all(self) -> None:
        settings = db.load_settings()
        new_val = not bool(settings.get("pause_all_replies", False))
        settings["pause_all_replies"] = new_val
        db.save_settings(settings)
        self._refresh_pause_button()
        if hasattr(self, "cfg_pause"):
            if new_val:
                self.cfg_pause.select()
            else:
                self.cfg_pause.deselect()

    def _refresh_pause_button(self) -> None:
        settings = db.load_settings()
        paused = bool(settings.get("pause_all_replies", False))
        if paused:
            self.header_pause_btn.configure(
                text="🙋 Humano al mando · tocá para reanudar",
                fg_color=COLORS["teal"],
                text_color="#0b2a33",
                hover_color="#6bb8ad",
            )
        else:
            self.header_pause_btn.configure(
                text="⏸ Pausar respuestas automáticas",
                fg_color=COLORS["danger"],
                text_color=COLORS["text"],
                hover_color="#c96850",
            )

    def _on_close(self) -> None:
        try:
            self._wa.stop()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()

    # —— WhatsApp ——
    def _build_whatsapp(self) -> None:
        tip = ctk.CTkFrame(self.tab_wa, fg_color=COLORS["surface2"], corner_radius=12)
        tip.pack(fill="x", padx=10, pady=(10, 8))
        ctk.CTkLabel(
            tip,
            text=(
                "Conectá el QR una vez. El bot cotiza corto, manda fotos de la habitación y solo reserva si el huésped dice sí."
            ),
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text"],
            wraplength=1100,
            justify="left",
        ).pack(anchor="w", padx=14, pady=10)

        body = ctk.CTkFrame(self.tab_wa, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=6, pady=4)

        # left: connection + inbox
        left = ctk.CTkFrame(body, fg_color=COLORS["surface2"], corner_radius=14, width=420)
        left.pack(side="left", fill="both", padx=(4, 8), pady=4)
        left.pack_propagate(False)

        ctk.CTkLabel(
            left,
            text="Conexión WhatsApp (QR)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkLabel(
            left,
            text="Abrí WhatsApp en el celu → Dispositivos vinculados → Vincular",
            text_color=COLORS["muted"],
            wraplength=380,
            justify="left",
        ).pack(anchor="w", padx=14)

        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(
            btns,
            text="Conectar / Mostrar QR",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self.wa_connect,
        ).pack(side="left")
        ctk.CTkButton(
            btns,
            text="Desvincular",
            fg_color="#243540",
            width=110,
            command=self.wa_logout,
        ).pack(side="left", padx=8)

        self.wa_status = ctk.CTkLabel(left, text="Listo para conectar", text_color=COLORS["muted"], anchor="w")
        self.wa_status.pack(fill="x", padx=14, pady=(0, 6))

        self.wa_qr = ctk.CTkLabel(left, text="El QR aparece acá", text_color=COLORS["muted"])
        self.wa_qr.pack(padx=14, pady=8)

        ctk.CTkLabel(
            left,
            text="Mensajes entrantes",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(8, 4))
        self.wa_list = ctk.CTkScrollableFrame(left, fg_color=COLORS["surface"], height=220)
        self.wa_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # center: paste / selected text
        mid = ctk.CTkFrame(body, fg_color=COLORS["surface2"], corner_radius=14)
        mid.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        ctk.CTkLabel(
            mid,
            text="Mensaje a analizar",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkLabel(
            mid,
            text="Historial del último mensaje procesado (manual solo si hace falta).",
            text_color=COLORS["muted"],
        ).pack(anchor="w", padx=14)
        self.inbox_text = ctk.CTkTextbox(mid, height=220, fg_color=COLORS["surface"])
        self.inbox_text.pack(fill="both", expand=True, padx=14, pady=10)
        self.inbox_text.insert(
            "1.0",
            "Hola! Soy Camila, somos 4, queremos dormitorio del 12 al 16 de enero. Gracias!",
        )
        mid_btns = ctk.CTkFrame(mid, fg_color="transparent")
        mid_btns.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(
            mid_btns,
            text="Procesar ahora (manual)",
            fg_color=COLORS["teal"],
            text_color="#0b2a33",
            hover_color="#6bb8ad",
            command=self.analyze_and_book_manual,
        ).pack(side="left")
        self.inbox_status = ctk.CTkLabel(mid, text="Esperando mensajes…", anchor="w")
        self.inbox_status.pack(fill="x", padx=14, pady=(0, 12))

        # right: detected fields
        right = ctk.CTkFrame(body, fg_color=COLORS["surface2"], corner_radius=14, width=360)
        right.pack(side="right", fill="y", padx=(8, 4), pady=4)
        right.pack_propagate(False)
        ctk.CTkLabel(
            right,
            text="Datos detectados",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(14, 6))
        form = ctk.CTkFrame(right, fg_color="transparent")
        form.pack(fill="x", padx=14)
        self.in_name = ctk.CTkEntry(form, placeholder_text="Nombre del huésped")
        self.in_name.pack(fill="x", pady=4)
        self.in_guests = ctk.CTkEntry(form, placeholder_text="Cantidad de personas")
        self.in_guests.pack(fill="x", pady=4)
        self.in_room = ctk.CTkOptionMenu(form, values=[f"{r['id']} · {r['name']}" for r in db.list_rooms()])
        self.in_room.pack(fill="x", pady=4)
        self.in_cin = ctk.CTkEntry(form, placeholder_text="Entrada YYYY-MM-DD")
        self.in_cin.pack(fill="x", pady=4)
        self.in_cout = ctk.CTkEntry(form, placeholder_text="Salida YYYY-MM-DD")
        self.in_cout.pack(fill="x", pady=4)
        self.in_price = ctk.CTkLabel(form, text="Precio: —", font=ctk.CTkFont(size=18, weight="bold"))
        self.in_price.pack(anchor="w", pady=10)
        self.in_photo = ctk.CTkLabel(right, text="")
        self.in_photo.pack(padx=12, pady=8)

    def wa_connect(self) -> None:
        self.set_status(self.wa_status, "Arrancando WhatsApp…", True)

        def work() -> None:
            try:
                self._wa.start()
                self.after(0, lambda: self.set_status(self.wa_status, "Esperando QR / sesión…", True))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.set_status(self.wa_status, str(exc), False))
                self.after(0, lambda: messagebox.showerror("WhatsApp", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def wa_logout(self) -> None:
        def work() -> None:
            try:
                self._wa.logout()
                self.after(0, lambda: self.set_status(self.wa_status, "Sesión cerrada. Escaneá de nuevo.", True))
                self.after(0, lambda: self.wa_qr.configure(image=None, text="El QR aparece acá"))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.set_status(self.wa_status, str(exc), False))

        threading.Thread(target=work, daemon=True).start()

    def _on_wa_status(self, st: dict[str, Any]) -> None:
        self.after(0, lambda: self._apply_wa_status(st))

    def _apply_wa_status(self, st: dict[str, Any]) -> None:
        if st.get("connected"):
            phone = st.get("phone") or ""
            self.header_wa.configure(text=f"WhatsApp: conectado {phone}", text_color=COLORS["ok"])
            self.set_status(self.wa_status, f"Conectado · {phone}", True)
            self.wa_qr.configure(image=None, text="✓ Vinculado\nLos mensajes nuevos aparecen abajo", text_color=COLORS["ok"])
        else:
            self.header_wa.configure(text="WhatsApp: esperando QR", text_color=COLORS["muted"])
            qr = st.get("qr")
            if qr and qr.startswith("data:image"):
                try:
                    b64 = qr.split(",", 1)[1]
                    raw = base64.b64decode(b64)
                    img = Image.open(io.BytesIO(raw)).convert("RGB")
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(260, 260))
                    self._photo_refs.append(ctk_img)
                    self.wa_qr.configure(image=ctk_img, text="")
                    self.set_status(self.wa_status, "Escaneá este QR con el celular", True)
                except Exception:  # noqa: BLE001
                    pass
            if st.get("error"):
                self.set_status(self.wa_status, f"Estado: {st['error']}", False)

        # pull messages + auto-book
        try:
            msgs = self._wa.messages(since=self._wa_last_msg_id)
            if msgs:
                self._wa_last_msg_id = max(m["id"] for m in msgs)
                for m in reversed(msgs):
                    self._wa_messages.insert(0, m)
                self._render_wa_messages()
                self._notify_new_messages(msgs)
                settings = db.load_settings()
                if settings.get("auto_book", True):
                    for m in msgs:
                        mid = int(m.get("id") or 0)
                        if mid in self._wa_processed_ids:
                            continue
                        text = (m.get("text") or "").strip()
                        if not text or not self._looks_like_booking(text):
                            m["auto_status"] = "Ignorado (no parece reserva)"
                            continue
                        self._wa_processed_ids.add(mid)
                        self.inbox_text.delete("1.0", "end")
                        self.inbox_text.insert("1.0", text)
                        self._process_text_async(
                            text,
                            from_name=str(m.get("from") or ""),
                            auto_book=True,
                            msg_id=mid,
                            jid=str(m.get("jid") or ""),
                        )
        except Exception:  # noqa: BLE001
            pass

    def _notify_new_messages(self, msgs: list[dict]) -> None:
        try:
            settings = db.load_settings()
            if not settings.get("notify_new_messages", True):
                return
        except Exception:  # noqa: BLE001
            return
        if not msgs:
            return
        first = msgs[0]
        sender = str(first.get("from") or "WhatsApp")
        preview = (str(first.get("text") or "").strip())[:80] or "Nuevo mensaje"
        title = "Nuevo mensaje de WhatsApp" if len(msgs) == 1 else f"{len(msgs)} mensajes nuevos de WhatsApp"
        threading.Thread(
            target=_send_windows_notification,
            args=(title, f"{sender}: {preview}"),
            daemon=True,
        ).start()

    def _render_wa_messages(self) -> None:
        for child in self.wa_list.winfo_children():
            child.destroy()
        if not self._wa_messages:
            ctk.CTkLabel(self.wa_list, text="Todavía no hay mensajes.", text_color=COLORS["muted"]).pack(
                anchor="w", padx=6, pady=6
            )
            return
        for msg in self._wa_messages[:40]:
            card = ctk.CTkFrame(self.wa_list, fg_color=COLORS["surface2"], corner_radius=10)
            card.pack(fill="x", padx=4, pady=4)
            preview = (msg.get("text") or "")[:120]
            status = msg.get("auto_status") or "En cola / sin procesar"
            jid = str(msg.get("jid") or "")
            ctk.CTkLabel(
                card,
                text=f"{msg.get('from', 'Contacto')}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS["teal"],
                anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 0))
            ctk.CTkLabel(
                card,
                text=preview,
                text_color=COLORS["text"],
                wraplength=340,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(
                card,
                text=status,
                text_color=COLORS["ok"] if msg.get("auto_ok") else COLORS["muted"],
                wraplength=340,
                justify="left",
                anchor="w",
                font=ctk.CTkFont(size=11),
            ).pack(fill="x", padx=10, pady=(0, 4))

            reply_preview = msg.get("auto_reply") or msg.get("draft_reply")
            if reply_preview:
                ctk.CTkLabel(
                    card,
                    text=f"↳ {reply_preview[:200]}",
                    text_color=COLORS["teal"],
                    wraplength=340,
                    justify="left",
                    anchor="w",
                    font=ctk.CTkFont(size=11),
                ).pack(fill="x", padx=10, pady=(0, 4))

            has_photo = (
                msg.get("photo_path")
                or msg.get("photo_paths")
                or msg.get("draft_photo_path")
                or msg.get("draft_photo_paths")
            )
            if has_photo:
                note = "📷 foto en borrador (sin enviar)" if msg.get("draft_pending") else "📷 foto enviada"
                ctk.CTkLabel(
                    card,
                    text=note,
                    text_color=COLORS["muted"],
                    anchor="w",
                    font=ctk.CTkFont(size=11),
                ).pack(fill="x", padx=10, pady=(0, 4))

            action_row = ctk.CTkFrame(card, fg_color="transparent")
            action_row.pack(fill="x", padx=10, pady=(0, 8))
            if jid:
                paused_chat = db.is_chat_paused(jid)
                ctk.CTkButton(
                    action_row,
                    text="▶ Reanudar chat" if paused_chat else "⏸ Pausar este chat",
                    width=140,
                    height=24,
                    font=ctk.CTkFont(size=11),
                    fg_color=COLORS["teal"] if paused_chat else "#243540",
                    text_color="#0b2a33" if paused_chat else COLORS["text"],
                    hover_color="#6bb8ad" if paused_chat else "#2d4552",
                    command=lambda j=jid: self._toggle_chat_pause(j),
                ).pack(side="left", padx=(0, 6))
            if msg.get("draft_pending"):
                ctk.CTkButton(
                    action_row,
                    text="Enviar",
                    width=80,
                    height=24,
                    font=ctk.CTkFont(size=11),
                    fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"],
                    command=lambda mm=msg: self._send_draft(mm),
                ).pack(side="left")

    def _toggle_chat_pause(self, jid: str) -> None:
        if not jid:
            return
        db.set_chat_paused(jid, not db.is_chat_paused(jid))
        self._render_wa_messages()

    def _send_draft(self, msg: dict[str, Any]) -> None:
        jid = str(msg.get("jid") or "")
        if not jid:
            messagebox.showwarning("Enviar", "Este mensaje no tiene un chat de WhatsApp asociado.")
            return
        text = msg.get("draft_reply") or ""
        photo_path = msg.get("draft_photo_path")
        photo_paths = msg.get("draft_photo_paths")

        def work() -> None:
            ok = self._maybe_send_wa(jid, text, photo_path=photo_path, photo_paths=photo_paths)

            def done() -> None:
                msg["draft_pending"] = False
                msg["auto_status"] = "✓ Enviado manualmente" if ok else "✗ No se pudo enviar (reintentá)"
                msg["auto_ok"] = ok
                self._render_wa_messages()
                self.set_status(
                    self.inbox_status,
                    "Respuesta enviada ✓" if ok else "No se pudo enviar la respuesta",
                    ok,
                )

            self.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _use_wa_message(self, text: str, from_name: str = "", jid: str = "") -> None:
        self.inbox_text.delete("1.0", "end")
        self.inbox_text.insert("1.0", text)
        self._process_text_async(text, from_name=from_name, auto_book=True, jid=jid)

    def analyze_and_book_manual(self) -> None:
        text = self.inbox_text.get("1.0", "end").strip()
        self._process_text_async(text, from_name="", auto_book=True, jid="")

    def analyze_inbox(self) -> None:
        self.analyze_and_book_manual()

    def _looks_like_booking(self, text: str) -> bool:
        lower = text.lower()
        has_date = any(
            x in lower
            for x in (
                "enero",
                "febrero",
                "marzo",
                "abril",
                "mayo",
                "junio",
                "julio",
                "agosto",
                "septiembre",
                "octubre",
                "noviembre",
                "diciembre",
                "/",
                "-",
                "noche",
                "del ",
                "al ",
            )
        )
        has_intent = any(
            x in lower
            for x in ("reserva", "habit", "dorm", "suite", "cama", "persona", "somos", "pax", "disponib", "quiero", "busco")
        )
        return has_date or has_intent

    def _process_text_async(
        self,
        text: str,
        *,
        from_name: str = "",
        auto_book: bool = True,
        msg_id: int | None = None,
        jid: str = "",
    ) -> None:
        text = (text or "").strip()
        if not text:
            self.set_status(self.inbox_status, "Sin texto para procesar", False)
            return
        self.set_status(self.inbox_status, "Procesando automáticamente…", True)

        def work() -> None:
            try:
                result = self._auto_book_from_text(
                    text, from_name=from_name, auto_book=auto_book, jid=jid
                )
                self.after(0, lambda: self._on_auto_done(result, msg_id=msg_id, text=text))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.set_status(self.inbox_status, str(exc), False))

        threading.Thread(target=work, daemon=True).start()

    def _auto_book_from_text(
        self,
        text: str,
        *,
        from_name: str = "",
        auto_book: bool = True,
        jid: str = "",
    ) -> dict[str, Any]:
        settings = db.load_settings()
        out: dict[str, Any] = {
            "parsed": {},
            "booked": False,
            "error": None,
            "res_id": None,
            "reply": None,
            "replied": False,
            "quoted": False,
            "cancelled": False,
        }
        if not auto_book or not settings.get("auto_book", True):
            parsed = ai_parser.extract_reservation(text)
            out["parsed"] = parsed
            return out

        flow = wa_flow.handle_message(text, jid=jid, from_name=from_name)
        out["parsed"] = flow.get("parsed") or {}
        out["booked"] = bool(flow.get("booked"))
        out["res_id"] = flow.get("res_id")
        out["error"] = flow.get("error")
        out["quoted"] = bool(flow.get("quoted"))
        out["cancelled"] = bool(flow.get("cancelled"))
        out["payload"] = flow.get("payload")
        out["phase"] = flow.get("phase")
        out["reply"] = flow.get("reply")
        out["photo_path"] = flow.get("photo_path")
        out["photo_paths"] = flow.get("photo_paths")
        out["paused"] = bool(flow.get("paused"))

        if out["paused"]:
            return out

        auto_reply = bool(settings.get("auto_reply", True))
        semi_auto = bool(settings.get("semi_auto", False))
        if auto_reply and (out["reply"] or out.get("photo_path") or out.get("photo_paths")):
            if semi_auto:
                out["draft_pending"] = True
                out["replied"] = False
            else:
                out["replied"] = self._maybe_send_wa(
                    jid,
                    out["reply"] or "",
                    photo_path=out.get("photo_path"),
                    photo_paths=out.get("photo_paths"),
                )
        return out

    def _maybe_send_wa(
        self,
        jid: str,
        text: str,
        photo_path: str | None = None,
        photo_paths: list[str] | None = None,
    ) -> bool:
        if not jid:
            return False
        paths = list(photo_paths) if photo_paths else ([photo_path] if photo_path else [])
        if not text and not paths:
            return False
        try:
            if paths:
                processed: list[str] = []
                for p in paths:
                    try:
                        ready = media_util.prepare_wa_image(Path(p)) if media_util else Path(p)
                        processed.append(str(ready))
                    except Exception:  # noqa: BLE001
                        processed.append(str(p))
                if len(processed) > 1:
                    self._wa.send_images(jid, processed, caption=text or "")
                else:
                    self._wa.send_image(jid, processed[0], caption=text or "")
            else:
                self._wa.send_message(jid, text)
            return True
        except Exception:  # noqa: BLE001
            return False

    def _on_auto_done(self, result: dict[str, Any], *, msg_id: int | None, text: str) -> None:
        if result.get("paused"):
            self._handle_paused_result(msg_id)
            return

        parsed = result.get("parsed") or {}
        self._apply_parsed(parsed)
        reply_bit = ""
        if result.get("reply"):
            if result.get("draft_pending"):
                reply_bit = " · borrador pendiente de envío (semi-auto)"
            elif result.get("replied"):
                reply_bit = " · respondió WA"
            else:
                reply_bit = " · respuesta lista (sin jid/WA)"

        if msg_id is not None:
            for m in self._wa_messages:
                if m.get("id") == msg_id:
                    if result.get("booked"):
                        m["auto_ok"] = True
                        m["auto_status"] = f"✓ Reserva #{result['res_id']}{reply_bit}"
                    elif result.get("cancelled"):
                        m["auto_ok"] = True
                        m["auto_status"] = f"Cancelada #{result.get('res_id')}{reply_bit}"
                    elif result.get("quoted"):
                        m["auto_ok"] = True
                        m["auto_status"] = f"Cotización (sin reservar){reply_bit}"
                    else:
                        m["auto_ok"] = False
                        m["auto_status"] = (result.get("error") or result.get("phase") or "Pendiente") + reply_bit
                    if result.get("reply"):
                        m["auto_reply"] = result["reply"]
                    if result.get("photo_path"):
                        m["photo_path"] = result["photo_path"]
                    if result.get("photo_paths"):
                        m["photo_paths"] = result["photo_paths"]
                    if result.get("draft_pending"):
                        m["draft_pending"] = True
                        m["draft_reply"] = result.get("reply")
                        m["draft_photo_path"] = result.get("photo_path")
                        m["draft_photo_paths"] = result.get("photo_paths")
                    else:
                        m["draft_pending"] = False
                    break
            self._render_wa_messages()

        if result.get("booked"):
            payload = result.get("payload") or {}
            self.refresh_calendar()
            self.set_status(
                self.inbox_status,
                f"✓ Reserva #{result['res_id']} · {payload.get('guest_name')} · "
                f"USD {payload.get('price_usd', 0):.0f}{reply_bit}",
                True,
            )
        elif result.get("cancelled"):
            self.refresh_calendar()
            self.set_status(self.inbox_status, f"Reserva cancelada #{result.get('res_id')}{reply_bit}", True)
        elif result.get("quoted"):
            payload = result.get("payload") or {}
            self.set_status(
                self.inbox_status,
                f"Cotización sin reservar · USD {payload.get('price_usd', 0):.0f}{reply_bit}",
                True,
            )
        else:
            err = result.get("error") or result.get("phase") or "En conversación"
            self.set_status(self.inbox_status, f"{err}{reply_bit}", False)
            if result.get("reply") and not result.get("replied"):
                self.inbox_text.insert("end", f"\n\n—— Borrador respuesta ——\n{result['reply']}")

    def _handle_paused_result(self, msg_id: int | None) -> None:
        if msg_id is not None:
            for m in self._wa_messages:
                if m.get("id") == msg_id:
                    m["auto_ok"] = True
                    m["auto_status"] = "🙋 Humano al mando (bot pausado)"
                    break
            self._render_wa_messages()
        self.set_status(
            self.inbox_status,
            "🙋 Humano al mando — respuestas automáticas pausadas, respondé manualmente",
            True,
        )

    def _apply_parsed(self, parsed: dict) -> None:
        self._inbox_parsed = parsed
        if parsed.get("guest_name"):
            self.in_name.delete(0, "end")
            self.in_name.insert(0, parsed["guest_name"])
        if parsed.get("guests"):
            self.in_guests.delete(0, "end")
            self.in_guests.insert(0, str(parsed["guests"]))
        if parsed.get("room_id"):
            for opt in self.in_room.cget("values"):
                if opt.startswith(parsed["room_id"]):
                    self.in_room.set(opt)
                    break
        if parsed.get("check_in"):
            self.in_cin.delete(0, "end")
            self.in_cin.insert(0, parsed["check_in"])
        if parsed.get("check_out"):
            self.in_cout.delete(0, "end")
            self.in_cout.insert(0, parsed["check_out"])
        self._refresh_inbox_quote()
        self.set_status(
            self.inbox_status,
            f"Motor: {parsed.get('engine')} · confianza {parsed.get('confidence', 0):.0%}",
            True,
        )

    def _selected_room_id(self, menu: ctk.CTkOptionMenu) -> str:
        return menu.get().split(" · ")[0].strip()

    def _refresh_inbox_quote(self) -> None:
        try:
            guests = int(self.in_guests.get().strip() or "0")
            room_id = self._selected_room_id(self.in_room)
            cin = pricing.parse_date(self.in_cin.get())
            cout = pricing.parse_date(self.in_cout.get())
            validated = pricing.validate_booking(
                guest_name=self.in_name.get() or "Huésped",
                guests=guests or 1,
                room_id=room_id,
                check_in=cin,
                check_out=cout,
            )
            self.in_price.configure(
                text=f"Precio: USD {validated['price_usd']:.0f} · {validated['nights']} noches"
            )
            img = self.room_photo(room_id, size=(320, 180))
            if img:
                self.in_photo.configure(image=img, text="")
        except Exception as exc:  # noqa: BLE001
            self.in_price.configure(text=f"Precio: — ({exc})")

    def confirm_from_inbox(self) -> None:
        try:
            guests = int(self.in_guests.get().strip())
            room_id = self._selected_room_id(self.in_room)
            payload = pricing.validate_booking(
                guest_name=self.in_name.get(),
                guests=guests,
                room_id=room_id,
                check_in=pricing.parse_date(self.in_cin.get()),
                check_out=pricing.parse_date(self.in_cout.get()),
            )
            res_id = db.create_reservation(
                {
                    **payload,
                    "source": "whatsapp-ai",
                    "notes": (self._inbox_parsed or {}).get("notes"),
                }
            )
            self.refresh_calendar()
            self.set_status(self.inbox_status, f"Reserva #{res_id} creada para {payload['guest_name']}", True)
            messagebox.showinfo(
                "Reserva creada",
                f"{payload['guest_name']}\n{payload['room']['name']}\n"
                f"{payload['check_in']} → {payload['check_out']}\nUSD {payload['price_usd']:.0f}",
            )
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.inbox_status, str(exc), False)
            messagebox.showerror("No se pudo reservar", str(exc))

    # —— Nueva reserva ——
    def _build_new(self) -> None:
        wrap = ctk.CTkScrollableFrame(self.tab_new, fg_color="transparent")
        wrap.pack(fill="both", expand=True)
        ctk.CTkLabel(
            wrap,
            text="Creá una reserva a mano (sin WhatsApp)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=12, pady=(10, 4))
        grid = ctk.CTkFrame(wrap, fg_color=COLORS["surface2"], corner_radius=12)
        grid.pack(fill="x", padx=8, pady=8)

        self.n_name = ctk.CTkEntry(grid, placeholder_text="Nombre del huésped", width=280)
        self.n_name.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.n_guests = ctk.CTkEntry(grid, placeholder_text="Cantidad de personas", width=180)
        self.n_guests.grid(row=0, column=1, padx=10, pady=10)
        self.n_cin = ctk.CTkEntry(grid, placeholder_text="Entrada YYYY-MM-DD", width=180)
        self.n_cin.grid(row=1, column=0, padx=10, pady=10)
        self.n_cout = ctk.CTkEntry(grid, placeholder_text="Salida YYYY-MM-DD", width=180)
        self.n_cout.grid(row=1, column=1, padx=10, pady=10)
        self.n_room = ctk.CTkOptionMenu(grid, values=["(elegí personas primero)"], width=280)
        self.n_room.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(grid, text="Filtrar habitaciones", command=self.filter_rooms).grid(
            row=2, column=1, padx=10, pady=10
        )
        ctk.CTkButton(grid, text="Calcular precio + foto", command=self.preview_new).grid(
            row=3, column=0, padx=10, pady=12
        )
        ctk.CTkButton(
            grid,
            text="Confirmar reserva",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self.save_new,
        ).grid(row=3, column=1, padx=10, pady=12)

        self.n_price = ctk.CTkLabel(wrap, text="Precio: —", font=ctk.CTkFont(size=22, weight="bold"))
        self.n_price.pack(anchor="w", padx=14, pady=6)
        self.n_meta = ctk.CTkLabel(wrap, text="", justify="left")
        self.n_meta.pack(anchor="w", padx=14)
        self.n_photo = ctk.CTkLabel(wrap, text="")
        self.n_photo.pack(padx=14, pady=12)
        self.n_status = ctk.CTkLabel(wrap, text="")
        self.n_status.pack(anchor="w", padx=14, pady=6)

    def filter_rooms(self) -> None:
        try:
            guests = int(self.n_guests.get().strip())
            options = pricing.rooms_for_guests(guests)
            if not options:
                raise ValueError("No hay habitaciones para esa cantidad")
            values = [f"{r['id']} · {r['name']} (hasta {r['capacity']})" for r in options]
            self.n_room.configure(values=values)
            self.n_room.set(values[0])
            self.set_status(self.n_status, f"{len(values)} habitación(es) posibles", True)
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.n_status, str(exc), False)

    def preview_new(self) -> None:
        try:
            guests = int(self.n_guests.get().strip())
            room_id = self.n_room.get().split(" · ")[0].strip()
            payload = pricing.validate_booking(
                guest_name=self.n_name.get() or "Huésped",
                guests=guests,
                room_id=room_id,
                check_in=pricing.parse_date(self.n_cin.get()),
                check_out=pricing.parse_date(self.n_cout.get()),
            )
            self.n_price.configure(text=f"USD {payload['price_usd']:.0f}")
            self.n_meta.configure(
                text=(
                    f"{payload['room']['name']} · {payload['guests']} personas · "
                    f"{payload['nights']} noches\n{payload['check_in']} → {payload['check_out']}"
                )
            )
            img = self.room_photo(room_id, size=(520, 300))
            if img:
                self.n_photo.configure(image=img, text="")
            self.set_status(self.n_status, "Disponible", True)
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.n_status, str(exc), False)

    def save_new(self) -> None:
        try:
            guests = int(self.n_guests.get().strip())
            room_id = self.n_room.get().split(" · ")[0].strip()
            payload = pricing.validate_booking(
                guest_name=self.n_name.get(),
                guests=guests,
                room_id=room_id,
                check_in=pricing.parse_date(self.n_cin.get()),
                check_out=pricing.parse_date(self.n_cout.get()),
            )
            res_id = db.create_reservation({**payload, "source": "manual"})
            self.refresh_calendar()
            self.set_status(self.n_status, f"Reserva #{res_id} guardada", True)
            messagebox.showinfo("Listo", f"Reserva #{res_id} creada")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    # —— Calendario ——
    def _build_calendar(self) -> None:
        top = ctk.CTkFrame(self.tab_cal, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(top, text="‹", width=40, command=lambda: self.shift_month(-1)).pack(side="left")
        self.cal_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.cal_label.pack(side="left", padx=12)
        ctk.CTkButton(top, text="›", width=40, command=lambda: self.shift_month(1)).pack(side="left")
        ctk.CTkButton(top, text="Hoy", width=70, command=self.goto_today).pack(side="left", padx=8)
        ctk.CTkLabel(top, text="● = hay reservas ese día", text_color=COLORS["muted"]).pack(side="left", padx=12)

        body = ctk.CTkFrame(self.tab_cal, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=8)
        self.cal_grid = ctk.CTkFrame(body, fg_color=COLORS["surface2"], corner_radius=12)
        self.cal_grid.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.day_panel = ctk.CTkScrollableFrame(body, width=360, fg_color=COLORS["surface2"], corner_radius=12)
        self.day_panel.pack(side="right", fill="y")
        ctk.CTkLabel(self.day_panel, text="Día seleccionado", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=8, pady=8
        )
        self.day_list = ctk.CTkLabel(self.day_panel, text="Elegí un día", justify="left", anchor="nw")
        self.day_list.pack(fill="both", expand=True, padx=8, pady=8)

    def shift_month(self, delta: int) -> None:
        m = self.cal_month + delta
        y = self.cal_year
        if m < 1:
            m = 12
            y -= 1
        elif m > 12:
            m = 1
            y += 1
        self.cal_month, self.cal_year = m, y
        self.refresh_calendar()

    def goto_today(self) -> None:
        today = date.today()
        self.cal_year, self.cal_month = today.year, today.month
        self.refresh_calendar()
        self.show_day(today)

    def refresh_calendar(self) -> None:
        for child in self.cal_grid.winfo_children():
            child.destroy()
        self.cal_label.configure(text=f"{MONTHS_ES[self.cal_month - 1]} {self.cal_year}")
        for i, name in enumerate(["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]):
            ctk.CTkLabel(self.cal_grid, text=name, width=70).grid(row=0, column=i, padx=2, pady=6)
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(self.cal_year, self.cal_month)
        reserved_days = set()
        for res in db.list_reservations(month=self.cal_month, year=self.cal_year):
            start = date.fromisoformat(res["check_in"])
            end = date.fromisoformat(res["check_out"])
            d = start
            while d < end:
                if d.month == self.cal_month and d.year == self.cal_year:
                    reserved_days.add(d.day)
                d = date.fromordinal(d.toordinal() + 1)

        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(self.cal_grid, text="", width=70, height=54).grid(row=r, column=c, padx=2, pady=2)
                    continue
                is_busy = day in reserved_days
                btn = ctk.CTkButton(
                    self.cal_grid,
                    text=str(day) + (" ●" if is_busy else ""),
                    width=70,
                    height=54,
                    fg_color=COLORS["accent"] if is_busy else COLORS["surface"],
                    hover_color=COLORS["accent_hover"] if is_busy else "#243540",
                    command=lambda d=day: self.show_day(date(self.cal_year, self.cal_month, d)),
                )
                btn.grid(row=r, column=c, padx=2, pady=2)

    def show_day(self, day: date) -> None:
        rows = db.reservations_on_day(day)
        if not rows:
            self.day_list.configure(text=f"{day.isoformat()}\n\nSin reservas.")
            return
        lines = [f"{day.isoformat()}", ""]
        for r in rows:
            lines.append(
                f"• {r['guest_name']} · {r['room_name']}\n"
                f"  {r['guests']} pers. · {r['check_in']} → {r['check_out']}\n"
                f"  USD {r['price_usd']:.0f} · #{r['id']} ({r['status']})"
            )
            lines.append("")
        self.day_list.configure(text="\n".join(lines))

        for child in list(self.day_panel.winfo_children()):
            if getattr(child, "_is_action", False):
                child.destroy()
        for r in rows:
            fr = ctk.CTkFrame(self.day_panel, fg_color="transparent")
            fr.pack(fill="x", padx=8, pady=2)
            fr._is_action = True  # type: ignore[attr-defined]
            ctk.CTkButton(
                fr,
                text=f"Cancelar #{r['id']}",
                width=120,
                fg_color="#243540",
                command=lambda i=r["id"]: self.cancel_res(i),
            ).pack(side="left")

    def cancel_res(self, res_id: int) -> None:
        if messagebox.askyesno("Cancelar", f"¿Cancelar reserva #{res_id}?"):
            db.cancel_reservation(res_id)
            self.refresh_calendar()
            self.day_list.configure(text="Reserva cancelada. Elegí un día.")

    # —— Tarifas ——
    def _build_rates(self) -> None:
        self.rates_frame = ctk.CTkScrollableFrame(self.tab_rates, fg_color="transparent")
        self.rates_frame.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(
            self.rates_frame,
            text="Tarifas USD / noche (mín – máx). El sistema usa el promedio salvo que cambies el modo en Config.",
            anchor="w",
            text_color=COLORS["muted"],
        ).pack(fill="x", padx=6, pady=6)
        self.rate_entries: dict[int, dict[str, ctk.CTkEntry | ctk.CTkOptionMenu]] = {}

    def refresh_rates(self) -> None:
        for child in self.rates_frame.winfo_children()[1:]:
            child.destroy()
        self.rate_entries.clear()
        for row in db.list_rates():
            month = int(row["month"])
            box = ctk.CTkFrame(self.rates_frame, fg_color=COLORS["surface2"], corner_radius=10)
            box.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(box, text=MONTHS_ES[month - 1], width=100, anchor="w").pack(side="left", padx=6)
            season = ctk.CTkOptionMenu(box, values=["alta", "media", "baja"], width=90)
            season.set(row["season"])
            season.pack(side="left", padx=4)
            fields = {}
            for key, label in (
                ("suite", "Privada"),
                ("doble", "Doble"),
                ("dorm", "Dorm"),
            ):
                ctk.CTkLabel(box, text=label, width=44).pack(side="left")
                e_min = ctk.CTkEntry(box, width=56)
                e_min.insert(0, str(int(row[f"{key}_min"])))
                e_min.pack(side="left", padx=2)
                e_max = ctk.CTkEntry(box, width=56)
                e_max.insert(0, str(int(row[f"{key}_max"])))
                e_max.pack(side="left", padx=2)
                fields[f"{key}_min"] = e_min
                fields[f"{key}_max"] = e_max
            fields["season"] = season
            self.rate_entries[month] = fields
        ctk.CTkButton(
            self.rates_frame,
            text="Guardar tarifas",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self.save_rates,
        ).pack(pady=12)

    def save_rates(self) -> None:
        try:
            for month, fields in self.rate_entries.items():
                db.upsert_rate(
                    month,
                    {
                        "season": fields["season"].get(),
                        "suite_min": float(fields["suite_min"].get()),
                        "suite_max": float(fields["suite_max"].get()),
                        "doble_min": float(fields["doble_min"].get()),
                        "doble_max": float(fields["doble_max"].get()),
                        "dorm_min": float(fields["dorm_min"].get()),
                        "dorm_max": float(fields["dorm_max"].get()),
                    },
                )
            messagebox.showinfo("Tarifas", "Tarifas guardadas")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    # —— Operador ——
    def _build_ops(self) -> None:
        wrap = ctk.CTkScrollableFrame(self.tab_ops, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            wrap,
            text=f"Panel del operador · {APP_NAME} v{APP_VERSION}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 10))

        # Resumen diario
        summary_box = ctk.CTkFrame(wrap, fg_color=COLORS["surface2"], corner_radius=12)
        summary_box.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            summary_box,
            text="Resumen de hoy",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(12, 4))
        self.ops_summary = ctk.CTkLabel(summary_box, text="—", justify="left", anchor="w")
        self.ops_summary.pack(anchor="w", padx=14, pady=(0, 6))
        ctk.CTkButton(
            summary_box, text="Actualizar resumen", width=160, command=self.refresh_daily_summary
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # Buscar reservas
        search_box = ctk.CTkFrame(wrap, fg_color=COLORS["surface2"], corner_radius=12)
        search_box.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            search_box,
            text="Buscar reservas",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(12, 4))
        search_row = ctk.CTkFrame(search_box, fg_color="transparent")
        search_row.pack(fill="x", padx=14)
        self.ops_search_entry = ctk.CTkEntry(
            search_row, placeholder_text="Nombre, WhatsApp, notas o #id"
        )
        self.ops_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.ops_search_entry.bind("<Return>", lambda _e: self.search_reservations())
        ctk.CTkButton(search_row, text="Buscar", width=90, command=self.search_reservations).pack(
            side="left"
        )
        self.ops_search_results = ctk.CTkScrollableFrame(
            search_box, fg_color=COLORS["surface"], height=220
        )
        self.ops_search_results.pack(fill="both", expand=True, padx=14, pady=(8, 14))

        # Ocupación de compartidas
        dorm_box = ctk.CTkFrame(wrap, fg_color=COLORS["surface2"], corner_radius=12)
        dorm_box.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            dorm_box,
            text="Ocupación de compartidas",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(12, 4))
        dorm_row = ctk.CTkFrame(dorm_box, fg_color="transparent")
        dorm_row.pack(fill="x", padx=14)
        ctk.CTkLabel(dorm_row, text="Día (YYYY-MM-DD):").pack(side="left")
        self.ops_dorm_date = ctk.CTkEntry(dorm_row, width=120)
        self.ops_dorm_date.insert(0, date.today().isoformat())
        self.ops_dorm_date.pack(side="left", padx=6)
        ctk.CTkButton(dorm_row, text="Hoy", width=60, command=self._ops_dorm_today).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(
            dorm_row, text="Ver ocupación", width=130, command=self.refresh_dorm_panel
        ).pack(side="left")
        self.ops_dorm_list = ctk.CTkLabel(dorm_box, text="—", justify="left", anchor="w")
        self.ops_dorm_list.pack(fill="x", padx=14, pady=(8, 14))

        # Recordatorios y reseñas
        remind_box = ctk.CTkFrame(wrap, fg_color=COLORS["surface2"], corner_radius=12)
        remind_box.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            remind_box,
            text="Recordatorios (48h antes) y pedido de reseña",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            remind_box,
            text="No se manda nada solo: revisá la lista y tocá enviar cuando quieras.",
            text_color=COLORS["muted"],
            justify="left",
        ).pack(anchor="w", padx=14)
        remind_row = ctk.CTkFrame(remind_box, fg_color="transparent")
        remind_row.pack(fill="x", padx=14, pady=(8, 4))
        ctk.CTkButton(
            remind_row, text="Enviar recordatorios pendientes", command=self.send_pending_reminders
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            remind_row, text="Enviar pedidos de reseña", command=self.send_pending_reviews
        ).pack(side="left")
        self.ops_remind_status = ctk.CTkLabel(remind_box, text="", anchor="w", justify="left")
        self.ops_remind_status.pack(fill="x", padx=14, pady=(4, 12))

        # Datos y conexión
        maint_box = ctk.CTkFrame(wrap, fg_color=COLORS["surface2"], corner_radius=12)
        maint_box.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            maint_box,
            text="Datos y conexión",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=14, pady=(12, 4))
        maint_row = ctk.CTkFrame(maint_box, fg_color="transparent")
        maint_row.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(
            maint_row, text="Respaldar base de datos", command=self.backup_database
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            maint_row, text="Exportar reservas (CSV)", command=self.export_reservations
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            maint_row, text="Reconectar bridge WhatsApp", command=self.reconnect_bridge
        ).pack(side="left")
        self.ops_status = ctk.CTkLabel(maint_box, text="", anchor="w", justify="left")
        self.ops_status.pack(fill="x", padx=14, pady=(0, 12))

        self.refresh_daily_summary()

    def refresh_daily_summary(self) -> None:
        s = db.daily_summary()
        self.ops_summary.configure(
            text=(
                f"{s['day']} · Consultas por WhatsApp: {s['consultations']} · "
                f"Reservas nuevas: {s['bookings']} · Canceladas: {s['cancelled']}"
            )
        )

    def search_reservations(self) -> None:
        q = self.ops_search_entry.get().strip()
        for child in self.ops_search_results.winfo_children():
            child.destroy()
        if not q:
            ctk.CTkLabel(
                self.ops_search_results, text="Escribí algo para buscar.", text_color=COLORS["muted"]
            ).pack(anchor="w", padx=6, pady=6)
            return
        rows = db.search_reservations(q)
        if not rows:
            ctk.CTkLabel(
                self.ops_search_results, text="Sin resultados.", text_color=COLORS["muted"]
            ).pack(anchor="w", padx=6, pady=6)
            return
        statuses = sorted(db.RESERVATION_STATUSES)
        for r in rows:
            card = ctk.CTkFrame(self.ops_search_results, fg_color=COLORS["surface2"], corner_radius=8)
            card.pack(fill="x", padx=4, pady=3)
            ctk.CTkLabel(
                card,
                text=f"#{r['id']} · {r['guest_name']} · {r['room_name']}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text"],
                anchor="w",
            ).pack(fill="x", padx=8, pady=(6, 0))
            ctk.CTkLabel(
                card,
                text=(
                    f"{r['check_in']} → {r['check_out']} · {r['guests']} pers. · "
                    f"USD {r['price_usd']:.0f} · {r['status']}"
                ),
                text_color=COLORS["muted"],
                anchor="w",
            ).pack(fill="x", padx=8)
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=(2, 8))
            status_menu = ctk.CTkOptionMenu(row, values=statuses, width=140)
            status_menu.set(r["status"])
            status_menu.pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                row,
                text="Guardar estado",
                width=110,
                command=lambda rid=r["id"], menu=status_menu: self._update_res_status(rid, menu.get()),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkButton(
                row,
                text="Exportar voucher",
                width=130,
                fg_color=COLORS["teal"],
                hover_color=COLORS["accent_hover"],
                command=lambda res=r: self._export_voucher(res),
            ).pack(side="left")

    def _export_voucher(self, reservation: dict[str, Any]) -> None:
        try:
            from . import voucher

            desktop = Path.home() / "Desktop"
            dest_dir = desktop if desktop.is_dir() else (DATA_DIR / "vouchers")
            path = voucher.save_voucher(reservation, dest_dir)
            self.set_status(self.ops_status, f"Voucher guardado en {path}", True)
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.ops_status, f"No se pudo generar el voucher: {exc}", False)

    def send_pending_reminders(self) -> None:
        try:
            from . import reminders

            due = reminders.due_reminders()
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.ops_remind_status, f"Error buscando recordatorios: {exc}", False)
            return
        if not due:
            self.set_status(self.ops_remind_status, "No hay recordatorios pendientes (check-in en 2 días).", True)
            return
        sent, failed = 0, 0
        for res in due:
            phone = (res.get("whatsapp") or "").strip()
            if not phone:
                failed += 1
                continue
            try:
                jid = f"{phone}@s.whatsapp.net"
                self._wa.send_message(jid, reminders.draft_reminder_message(res))
                reminders.mark_reminded(res["id"])
                sent += 1
            except Exception:  # noqa: BLE001
                failed += 1
        self.set_status(
            self.ops_remind_status,
            f"Recordatorios enviados: {sent} · sin WhatsApp/con error: {failed}",
            failed == 0,
        )

    def send_pending_reviews(self) -> None:
        try:
            from . import reminders

            due = reminders.due_reviews()
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.ops_remind_status, f"Error buscando pedidos de reseña: {exc}", False)
            return
        if not due:
            self.set_status(self.ops_remind_status, "No hay pedidos de reseña pendientes (check-out de ayer).", True)
            return
        sent, failed = 0, 0
        for res in due:
            phone = (res.get("whatsapp") or "").strip()
            if not phone:
                failed += 1
                continue
            try:
                jid = f"{phone}@s.whatsapp.net"
                self._wa.send_message(jid, reminders.draft_review_message(res))
                reminders.mark_reviewed(res["id"])
                sent += 1
            except Exception:  # noqa: BLE001
                failed += 1
        self.set_status(
            self.ops_remind_status,
            f"Pedidos de reseña enviados: {sent} · sin WhatsApp/con error: {failed}",
            failed == 0,
        )

    def _update_res_status(self, res_id: int, status: str) -> None:
        try:
            db.update_reservation_status(res_id, status)
            self.set_status(self.ops_status, f"Reserva #{res_id} → {status}", True)
            self.refresh_calendar()
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.ops_status, str(exc), False)

    def _ops_dorm_today(self) -> None:
        self.ops_dorm_date.delete(0, "end")
        self.ops_dorm_date.insert(0, date.today().isoformat())
        self.refresh_dorm_panel()

    def refresh_dorm_panel(self) -> None:
        day_str = self.ops_dorm_date.get().strip() or date.today().isoformat()
        try:
            date.fromisoformat(day_str)
        except ValueError:
            self.set_status(self.ops_status, "Fecha inválida (usá YYYY-MM-DD)", False)
            return
        rows = db.dorm_panel(day_str)
        if not rows:
            self.ops_dorm_list.configure(text="No hay habitaciones compartidas activas.")
            return
        lines = [
            f"{r['name']} — {r['occupied']}/{r['capacity']} ocupadas ({r['free']} libres)"
            for r in rows
        ]
        self.ops_dorm_list.configure(text="\n".join(lines))

    def backup_database(self) -> None:
        desktop = Path.home() / "Desktop"
        dest_dir = desktop if desktop.is_dir() else (DATA_DIR / "backups")
        try:
            path = db.backup_db(dest_dir)
            self.set_status(self.ops_status, f"Respaldo guardado en {path}", True)
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.ops_status, str(exc), False)

    def export_reservations(self) -> None:
        desktop = Path.home() / "Desktop"
        dest_dir = Path(desktop if desktop.is_dir() else (DATA_DIR / "backups"))
        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = dest_dir / f"reservas_{stamp}.csv"
        try:
            db.export_reservations_csv(path)
            self.set_status(self.ops_status, f"CSV exportado en {path}", True)
        except Exception as exc:  # noqa: BLE001
            self.set_status(self.ops_status, str(exc), False)

    def reconnect_bridge(self) -> None:
        self.set_status(self.ops_status, "Reconectando bridge de WhatsApp…", True)

        def work() -> None:
            try:
                self._wa.stop()
            except Exception:  # noqa: BLE001
                pass
            try:
                self._wa.start()
                self.after(
                    0, lambda: self.set_status(self.ops_status, "Bridge reiniciado, esperando estado…", True)
                )
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.set_status(self.ops_status, str(exc), False))

        threading.Thread(target=work, daemon=True).start()

    # —— Config ——
    def _build_config(self) -> None:
        settings = db.load_settings()
        wrap = ctk.CTkScrollableFrame(self.tab_cfg, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            wrap,
            text="IA gratuita (recomendado)",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            wrap,
            text=(
                "Qué tenés que hacer (2 minutos, gratis):\n"
                "1. Entrá a https://console.groq.com y creá cuenta\n"
                "2. Andá a API Keys → Create API Key\n"
                "3. Copiá la key (empieza con gsk_)\n"
                "4. Pegala abajo → Guardar configuración\n"
                "Con eso la app entiende mensajes raros mucho mejor.\n"
                "Sin key también funciona, pero con reglas más simples."
            ),
            justify="left",
            text_color=COLORS["muted"],
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(wrap, text="Proveedor", anchor="w").pack(fill="x")
        self.cfg_provider = ctk.CTkOptionMenu(
            wrap, values=["auto", "groq", "gemini", "openai", "rules"]
        )
        self.cfg_provider.set(settings.get("ai_provider", "auto"))
        self.cfg_provider.pack(anchor="w", pady=6)

        ctk.CTkLabel(wrap, text="Groq API key (gratis · recomendada)", anchor="w").pack(fill="x", pady=(10, 0))
        self.cfg_groq = ctk.CTkEntry(wrap, show="*", placeholder_text="gsk_...")
        self.cfg_groq.pack(fill="x", pady=6)
        if settings.get("groq_api_key"):
            self.cfg_groq.insert(0, settings["groq_api_key"])
        self.cfg_groq_model = ctk.CTkEntry(wrap, placeholder_text="Modelo Groq")
        self.cfg_groq_model.pack(fill="x", pady=4)
        self.cfg_groq_model.insert(0, settings.get("groq_model", "llama-3.3-70b-versatile"))

        ctk.CTkLabel(wrap, text="Gemini API key (gratis · Google AI Studio)", anchor="w").pack(
            fill="x", pady=(10, 0)
        )
        self.cfg_gemini = ctk.CTkEntry(wrap, show="*", placeholder_text="AIza...")
        self.cfg_gemini.pack(fill="x", pady=6)
        if settings.get("gemini_api_key"):
            self.cfg_gemini.insert(0, settings["gemini_api_key"])

        ctk.CTkLabel(wrap, text="OpenAI API key (opcional, de pago)", anchor="w").pack(fill="x", pady=(10, 0))
        self.cfg_key = ctk.CTkEntry(wrap, show="*", placeholder_text="sk-...")
        self.cfg_key.pack(fill="x", pady=6)
        if settings.get("openai_api_key"):
            self.cfg_key.insert(0, settings["openai_api_key"])

        ctk.CTkLabel(wrap, text="Modo de precio", anchor="w").pack(fill="x", pady=(10, 0))
        self.cfg_price = ctk.CTkOptionMenu(wrap, values=["min", "mid", "max"])
        self.cfg_price.set(settings.get("price_mode", "mid"))
        self.cfg_price.pack(anchor="w", pady=6)

        self.cfg_auto = ctk.CTkCheckBox(
            wrap,
            text="Reservar solo cuando llega un mensaje de WhatsApp (recomendado)",
        )
        if settings.get("auto_book", True):
            self.cfg_auto.select()
        self.cfg_auto.pack(anchor="w", pady=(12, 4))

        self.cfg_reply = ctk.CTkCheckBox(
            wrap,
            text="Responder solo por WhatsApp con Groq (pide datos / confirma reserva)",
        )
        if settings.get("auto_reply", True):
            self.cfg_reply.select()
        self.cfg_reply.pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(
            wrap,
            text="Modo operador",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(18, 4))

        self.cfg_pause = ctk.CTkCheckBox(
            wrap,
            text="Pausar TODAS las respuestas automáticas (humano al mando)",
        )
        if settings.get("pause_all_replies", False):
            self.cfg_pause.select()
        self.cfg_pause.pack(anchor="w", pady=(4, 4))

        self.cfg_semi_auto = ctk.CTkCheckBox(
            wrap,
            text="Modo semi-automático: preparar la respuesta pero no enviarla sola (revisar y tocar Enviar)",
        )
        if settings.get("semi_auto", False):
            self.cfg_semi_auto.select()
        self.cfg_semi_auto.pack(anchor="w", pady=(0, 4))

        self.cfg_notify = ctk.CTkCheckBox(
            wrap,
            text="Avisar en Windows cuando llega un mensaje nuevo de WhatsApp",
        )
        if settings.get("notify_new_messages", True):
            self.cfg_notify.select()
        self.cfg_notify.pack(anchor="w", pady=(0, 12))

        sleep_row = ctk.CTkFrame(wrap, fg_color="transparent")
        sleep_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sleep_row, text="El bot no responde solo entre", anchor="w").pack(side="left")
        self.cfg_sleep_start = ctk.CTkEntry(sleep_row, width=70, placeholder_text="00:00")
        self.cfg_sleep_start.insert(0, settings.get("bot_sleep_start", "00:00"))
        self.cfg_sleep_start.pack(side="left", padx=6)
        ctk.CTkLabel(sleep_row, text="y").pack(side="left")
        self.cfg_sleep_end = ctk.CTkEntry(sleep_row, width=70, placeholder_text="07:00")
        self.cfg_sleep_end.insert(0, settings.get("bot_sleep_end", "00:00"))
        self.cfg_sleep_end.pack(side="left", padx=6)

        deposit_row = ctk.CTkFrame(wrap, fg_color="transparent")
        deposit_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(deposit_row, text="Seña para confirmar reserva (%)", anchor="w").pack(side="left")
        self.cfg_deposit = ctk.CTkEntry(deposit_row, width=70)
        self.cfg_deposit.insert(0, str(round(float(settings.get("deposit_pct", 0.3)) * 100)))
        self.cfg_deposit.pack(side="left", padx=6)

        ctk.CTkLabel(
            wrap, text="Política de cancelación (se usa en respuestas de WhatsApp)", anchor="w"
        ).pack(fill="x", pady=(4, 0))
        self.cfg_cancel_policy = ctk.CTkTextbox(wrap, height=60)
        self.cfg_cancel_policy.pack(fill="x", pady=6)
        self.cfg_cancel_policy.insert("1.0", settings.get("cancellation_policy", ""))

        ctk.CTkButton(
            wrap,
            text="Guardar configuración",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self.save_config,
        ).pack(anchor="w", pady=16)

        ctk.CTkLabel(
            wrap,
            text=(
                "WhatsApp en vivo usa Node.js (gratis) + Baileys (no oficial).\n"
                "Instalá Node LTS si aún no lo tenés: https://nodejs.org\n"
                f"Base de datos: {db.DB_PATH}"
            ),
            justify="left",
            anchor="w",
            text_color=COLORS["muted"],
        ).pack(fill="x", pady=8)

    def save_config(self) -> None:
        settings = db.load_settings()
        settings["ai_provider"] = self.cfg_provider.get()
        settings["groq_api_key"] = self.cfg_groq.get().strip()
        settings["groq_model"] = self.cfg_groq_model.get().strip() or "llama-3.3-70b-versatile"
        settings["gemini_api_key"] = self.cfg_gemini.get().strip()
        settings["openai_api_key"] = self.cfg_key.get().strip()
        settings["price_mode"] = self.cfg_price.get()
        settings["auto_book"] = bool(self.cfg_auto.get())
        settings["auto_reply"] = bool(self.cfg_reply.get())
        settings["pause_all_replies"] = bool(self.cfg_pause.get())
        settings["semi_auto"] = bool(self.cfg_semi_auto.get())
        settings["notify_new_messages"] = bool(self.cfg_notify.get())
        settings["bot_sleep_start"] = self.cfg_sleep_start.get().strip() or "00:00"
        settings["bot_sleep_end"] = self.cfg_sleep_end.get().strip() or "07:00"
        try:
            settings["deposit_pct"] = max(0.0, min(1.0, float(self.cfg_deposit.get().strip() or "30") / 100))
        except ValueError:
            pass
        settings["cancellation_policy"] = self.cfg_cancel_policy.get("1.0", "end").strip()
        db.save_settings(settings)
        self._refresh_pause_button()
        messagebox.showinfo("Config", "Configuración guardada")


def run() -> None:
    app = ValizasApp()
    app.mainloop()


if __name__ == "__main__":
    run()
