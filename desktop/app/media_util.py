"""Media helpers: room photos, house album, WhatsApp-ready compression."""
from __future__ import annotations

from pathlib import Path

from .config import ASSETS_DIR, ASSETS_ROOMS, DATA_DIR, ROOMS

CACHE_DIR = DATA_DIR / "cache_wa_media"
PHOTO_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _room_stem(room_id: str) -> str | None:
    room = next((r for r in ROOMS if r["id"] == room_id), None)
    if not room:
        return None
    return Path(str(room.get("photo") or room_id)).stem


def _find_room_asset(stem: str) -> Path | None:
    """Look up `{stem}{ext}` under assets/rooms, preferring jpg (WhatsApp-friendly).

    Compares the resolved filename case-sensitively even though Windows
    filesystems are case-insensitive, since some room ids/stems only differ
    by case (e.g. "Hab_priv" vs "Hab_Priv_2") and a loose match would silently
    return another room's photo.
    """
    root = ASSETS_ROOMS.resolve()
    for ext in PHOTO_EXTS:
        path = (root / f"{stem}{ext}").resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.is_file() and path.stem == stem:
            return path
    return None


def room_photo_path(room_id: str) -> Path | None:
    """Main photo for a room, preferring jpg over webp for WhatsApp."""
    stem = _room_stem(room_id)
    if not stem:
        return None
    return _find_room_asset(stem)


def room_extra_photos(room_id: str) -> list[Path]:
    """Extra angles for a room ('más fotos'): _2 / _bath / _vista, plus house shots."""
    stem = _room_stem(room_id)
    paths: list[Path] = []
    if stem:
        for suffix in ("_2", "_bath", "_vista"):
            found = _find_room_asset(f"{stem}{suffix}")
            if found and found not in paths:
                paths.append(found)
    for house in house_album_paths():
        if house not in paths:
            paths.append(house)
        if len(paths) >= 5:
            break
    return paths


def house_album_paths() -> list[Path]:
    """Up to 3 general house photos (facade, common areas) for a first impression."""
    candidates = [
        ASSETS_DIR / "bg-front.webp",
        ASSETS_DIR / "bg-hero.webp",
        ASSETS_ROOMS / "extra.webp",
        ASSETS_ROOMS / "suite.webp",
        ASSETS_ROOMS / "rooms-generic.webp",
        ASSETS_DIR / "bg-night.webp",
        ASSETS_ROOMS / "doble.webp",
    ]
    found: list[Path] = []
    for path in candidates:
        if path.is_file() and path not in found:
            found.append(path)
        if len(found) >= 3:
            break
    return found


def compress_for_wa(src: Path, max_kb: int = 300) -> Path:
    """Return a jpg copy under `max_kb`, cached in DATA_DIR. Falls back to `src`."""
    src = Path(src)
    if not src.is_file():
        return src
    try:
        from PIL import Image
    except ImportError:
        return src

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CACHE_DIR / f"{src.stem}_wa.jpg"
    try:
        if out_path.is_file() and out_path.stat().st_mtime >= src.stat().st_mtime:
            return out_path

        img = Image.open(src)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        max_dim = 1600
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((round(img.width * ratio), round(img.height * ratio)))

        quality = 85
        while True:
            img.save(out_path, "JPEG", quality=quality, optimize=True)
            if out_path.stat().st_size <= max_kb * 1024 or quality <= 35:
                break
            quality -= 10
        return out_path
    except Exception:  # noqa: BLE001
        return src


def watermark_text(path: Path, text: str = "Valizas Hostel") -> Path:
    """Add a light watermark in the bottom-right corner. Mutates `path` in place."""
    path = Path(path)
    if not path.is_file():
        return path
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return path

    try:
        img = Image.open(path).convert("RGB")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font_size = max(14, img.width // 40)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:  # noqa: BLE001
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        margin = 10
        x = img.width - tw - margin * 2
        y = img.height - th - margin * 2

        draw.rectangle(
            (x - margin, y - margin, x + tw + margin, y + th + margin),
            fill=(0, 0, 0, 90),
        )
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 220))

        merged = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        merged.save(path, "JPEG", quality=88)
        return path
    except Exception:  # noqa: BLE001
        return path


def prepare_wa_image(path: Path, watermark: bool = True) -> Path:
    """Compress (and optionally watermark) an image before sending on WhatsApp."""
    path = Path(path)
    result = compress_for_wa(path)
    if watermark and result != path:
        result = watermark_text(result)
    return result
