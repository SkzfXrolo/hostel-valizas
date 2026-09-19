"""Cliente local del bridge WhatsApp (Baileys + Node)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .config import DATA_DIR, WA_AUTH_DIR, WA_BRIDGE_DIR, WA_BRIDGE_PORT


class WhatsAppBridge:
    def __init__(self, port: int = WA_BRIDGE_PORT) -> None:
        self.port = port
        self.base = f"http://127.0.0.1:{port}"
        self._proc: subprocess.Popen | None = None
        self._poll_thread: threading.Thread | None = None
        self._stop_poll = threading.Event()
        self.on_update: Callable[[dict[str, Any]], None] | None = None
        self.last_status: dict[str, Any] = {"ok": False, "connected": False, "qr": None}

    def node_available(self) -> bool:
        return shutil.which("node") is not None and shutil.which("npm") is not None

    def bridge_dir(self) -> Path:
        # Prefer sibling of EXE (writable) copy; fall back to bundled resources
        local = DATA_DIR.parent / "whatsapp-bridge"
        if (local / "package.json").exists():
            return local
        if (WA_BRIDGE_DIR / "package.json").exists():
            # copy once next to data for npm install writability
            if not local.exists():
                shutil.copytree(WA_BRIDGE_DIR, local, dirs_exist_ok=True)
            return local
        return WA_BRIDGE_DIR

    def ensure_deps(self) -> None:
        root = self.bridge_dir()
        if not (root / "package.json").exists():
            raise RuntimeError("No se encontró whatsapp-bridge. Reinstalá la app.")
        if (root / "node_modules" / "@whiskeysockets" / "baileys").exists():
            return
        npm = shutil.which("npm")
        if not npm:
            raise RuntimeError("Instalá Node.js (https://nodejs.org) para WhatsApp en vivo.")
        subprocess.check_call(
            [npm, "install", "--omit=dev"],
            cwd=str(root),
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

    def _get(self, path: str, timeout: float = 3.0) -> dict[str, Any]:
        req = urllib.request.Request(f"{self.base}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post(self, path: str, payload: dict | None = None, timeout: float = 8.0) -> dict[str, Any]:
        data = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def is_running(self) -> bool:
        try:
            self._get("/health", timeout=1.5)
            return True
        except Exception:  # noqa: BLE001
            return False

    def start(self) -> None:
        if not self.node_available():
            raise RuntimeError(
                "Para WhatsApp en vivo necesitás Node.js gratuito.\n"
                "Descargá LTS en https://nodejs.org e instalá, luego reintentá."
            )
        self.ensure_deps()
        if self.is_running():
            self._start_poll()
            return

        WA_AUTH_DIR.mkdir(parents=True, exist_ok=True)
        root = self.bridge_dir()
        node = shutil.which("node")
        env = os.environ.copy()
        env["WA_PORT"] = str(self.port)
        env["WA_AUTH_DIR"] = str(WA_AUTH_DIR)
        creation = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self._proc = subprocess.Popen(
            [node, "index.js"],
            cwd=str(root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation,
        )
        # wait for health
        for _ in range(40):
            time.sleep(0.25)
            if self.is_running():
                break
        else:
            raise RuntimeError("El bridge de WhatsApp no arrancó. ¿Puerto 8787 libre?")
        self._start_poll()

    def stop(self) -> None:
        self._stop_poll.set()
        try:
            if self.is_running():
                self._post("/stop")
        except Exception:  # noqa: BLE001
            pass
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def send_message(self, jid: str, text: str) -> dict[str, Any]:
        if not jid or not text:
            raise RuntimeError("Falta jid o texto para responder")
        return self._post("/send", {"jid": jid, "text": text}, timeout=20.0)

    def send_image(self, jid: str, image_path: str, caption: str = "") -> dict[str, Any]:
        if not jid or not image_path:
            raise RuntimeError("Falta jid o imagen para responder")
        path = Path(image_path)
        if not path.is_file():
            raise RuntimeError(f"Imagen no encontrada: {image_path}")
        payload: dict[str, Any] = {"jid": jid, "imagePath": str(path.resolve())}
        if caption:
            payload["text"] = caption
        return self._post("/send", payload, timeout=40.0)

    def send_images(self, jid: str, image_paths: list[str], caption: str = "") -> list[dict[str, Any]]:
        """Send several images one after another: first carries the caption, the
        rest go with a short/empty caption so the chat doesn't repeat the text."""
        if not jid or not image_paths:
            raise RuntimeError("Falta jid o imágenes para responder")
        results: list[dict[str, Any]] = []
        for i, path in enumerate(image_paths):
            cap = caption if i == 0 else ""
            results.append(self.send_image(jid, path, caption=cap))
            if i < len(image_paths) - 1:
                time.sleep(0.6)  # avoid bursting all images at once
        return results

    def logout(self) -> None:
        try:
            self._post("/logout")
        except Exception:  # noqa: BLE001
            pass

    def status(self) -> dict[str, Any]:
        try:
            self.last_status = self._get("/status")
        except Exception as exc:  # noqa: BLE001
            self.last_status = {"ok": False, "connected": False, "error": str(exc), "qr": None}
        return self.last_status

    def messages(self, since: int = 0) -> list[dict[str, Any]]:
        try:
            data = self._get(f"/messages?since={since}")
            return data.get("messages") or []
        except Exception:  # noqa: BLE001
            return []

    def _start_poll(self) -> None:
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._stop_poll.clear()

        def loop() -> None:
            while not self._stop_poll.is_set():
                st = self.status()
                if self.on_update:
                    try:
                        self.on_update(st)
                    except Exception:  # noqa: BLE001
                        pass
                time.sleep(1.2)

        self._poll_thread = threading.Thread(target=loop, daemon=True)
        self._poll_thread.start()
