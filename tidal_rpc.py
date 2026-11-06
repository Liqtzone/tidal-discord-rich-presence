"""
TIDAL -> Discord Rich Presence (Windows)

Reads the active TIDAL track from Windows media controls and looks up album art
and links in TIDAL's catalog API. Set TIDAL_CLIENT_ID and TIDAL_CLIENT_SECRET
in the environment before starting the program.
"""

import asyncio
import base64
import ctypes
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from ctypes import wintypes
from pathlib import Path

import requests
from dotenv import load_dotenv
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem
from pypresence import AioPresence, ActivityType
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)


PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "").strip()
TIDAL_CLIENT_ID = os.getenv("TIDAL_CLIENT_ID", "").strip()
TIDAL_CLIENT_SECRET = os.getenv("TIDAL_CLIENT_SECRET", "").strip()
TIDAL_COUNTRY_CODE = os.getenv("TIDAL_COUNTRY_CODE", "TR").strip().upper()

POLL_SECONDS = 2
MIN_UPDATE_GAP = 5
PLAYING = 4

API_BASE = "https://openapi.tidal.com/v2"
TOKEN_URL = "https://auth.tidal.com/v1/oauth2/token"
cache: dict[tuple[str, str, str], dict | None] = {}
access_token: str | None = None
token_expires_at = 0.0
_single_instance_handle = None


def configure_logging() -> logging.Logger:
    log_dir = Path(os.getenv("LOCALAPPDATA", Path.home())) / "TidalRPC" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("tidal_rpc")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_dir / "tidal-rpc.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(handler)
        if sys.stderr is not None:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(handler.formatter)
            logger.addHandler(console_handler)
    return logger


logger = configure_logging()


def acquire_single_instance() -> bool:
    """Keep a Windows mutex open so startup and manual launches cannot duplicate."""
    global _single_instance_handle
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    create_mutex.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    ctypes.set_last_error(0)
    handle = create_mutex(None, False, "Local\\TidalDiscordRichPresence")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        close_handle(handle)
        return False
    _single_instance_handle = handle
    return True


def artist_matches(candidate: str, wanted: str) -> bool:
    a, b = candidate.casefold().strip(), wanted.casefold().strip()
    return bool(a and b and (a in b or b in a))


def _get_access_token() -> str:
    global access_token, token_expires_at
    if access_token and time.time() < token_expires_at - 60:
        return access_token
    if not TIDAL_CLIENT_ID or not TIDAL_CLIENT_SECRET:
        raise RuntimeError(
            "TIDAL API anahtarlari ayarlanmamis. TIDAL_CLIENT_ID ve "
            "TIDAL_CLIENT_SECRET ortam degiskenlerini tanimla."
        )

    basic = base64.b64encode(
        f"{TIDAL_CLIENT_ID}:{TIDAL_CLIENT_SECRET}".encode("utf-8")
    ).decode("ascii")
    response = requests.post(
        TOKEN_URL,
        headers={"Authorization": f"Basic {basic}"},
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    response.raise_for_status()
    body = response.json()
    access_token = body["access_token"]
    token_expires_at = time.time() + int(body.get("expires_in", 3600))
    return access_token


def _resource_key(resource: dict) -> tuple[str, str]:
    return str(resource.get("type", "")), str(resource.get("id", ""))


def _relation_ids(resource: dict, relation_name: str) -> list[str]:
    relation = resource.get("relationships", {}).get(relation_name, {})
    data = relation.get("data") or []
    if isinstance(data, dict):
        data = [data]
    return [str(item.get("id", "")) for item in data if item.get("id")]


def _artwork_url(artwork: dict | None) -> str | None:
    if not artwork:
        return None
    attrs = artwork.get("attributes", {})
    url = attrs.get("url") or attrs.get("imageUrl") or attrs.get("image_url")
    files = attrs.get("files") or []
    if not url and files:
        largest = max(
            files,
            key=lambda item: int(item.get("meta", {}).get("width", 0) or 0),
        )
        url = largest.get("href")
    if url:
        return str(url).replace("{width}", "640").replace("{height}", "640")

    # Some TIDAL responses provide the artwork UUID instead of the CDN URL.
    art_id = artwork.get("id", "").replace("-", "")
    if re.fullmatch(r"[0-9a-fA-F]{32}", art_id):
        art_id = f"{art_id[:8]}-{art_id[8:12]}-{art_id[12:16]}-{art_id[16:20]}-{art_id[20:]}"
        return f"https://resources.tidal.com/images/{art_id}/640x640.jpg"
    return None


def lookup(title: str, artist: str, album: str) -> dict | None:
    key = (title, artist, album)
    if key in cache:
        return cache[key]

    try:
        response = requests.get(
            f"{API_BASE}/searchResults",
            headers={
                "Authorization": f"Bearer {_get_access_token()}",
                "Accept": "application/vnd.api+json",
            },
            params={
                "filter[query]": f"{title} {artist}",
                "countryCode": TIDAL_COUNTRY_CODE,
                "include": "tracks.albums,tracks.artists,tracks.albums.coverArt",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        included = payload.get("included", [])
        by_key = {_resource_key(item): item for item in included}

        track_ids: list[str] = []
        for result in payload.get("data", []):
            track_ids.extend(_relation_ids(result, "tracks"))
        tracks = [by_key.get(("tracks", track_id)) for track_id in track_ids]
        tracks = [track for track in tracks if track]

        best = None
        for track in tracks:
            attrs = track.get("attributes", {})
            track_title = str(attrs.get("title", ""))
            artist_ids = _relation_ids(track, "artists")
            track_artists = [
                str(by_key.get(("artists", artist_id), {}).get("attributes", {}).get("name", ""))
                for artist_id in artist_ids
            ]
            if not artist_matches(track_title, title):
                continue
            if track_artists and not any(artist_matches(name, artist) for name in track_artists):
                continue
            album_ids = _relation_ids(track, "albums")
            track_album = next(
                (by_key.get(("albums", album_id)) for album_id in album_ids if by_key.get(("albums", album_id))),
                None,
            )
            track_album_name = str(track_album.get("attributes", {}).get("title", "")) if track_album else ""
            if album and track_album_name.casefold() == album.casefold():
                best = (track, track_album, track_artists)
                break
            if best is None:
                best = (track, track_album, track_artists)

        if best:
            track, album_resource, track_artists = best
            track_id = str(track.get("id", ""))
            album_id = str(album_resource.get("id", "")) if album_resource else ""
            album_name = str(album_resource.get("attributes", {}).get("title", "")) if album_resource else album
            artist_ids = _relation_ids(track, "artists")
            artist_id = artist_ids[0] if artist_ids else ""

            cover_url = None
            if album_resource:
                cover_ids = _relation_ids(album_resource, "coverArt")
                artwork = next(
                    (by_key.get(("artworks", art_id)) for art_id in cover_ids if by_key.get(("artworks", art_id))),
                    None,
                )
                cover_url = _artwork_url(artwork)

            info = {
                "track_url": f"https://tidal.com/browse/track/{track_id}",
                "album_url": f"https://tidal.com/browse/album/{album_id}" if album_id else f"https://tidal.com/",
                "artist_url": f"https://tidal.com/browse/artist/{artist_id}" if artist_id else f"https://tidal.com/",
                "cover": cover_url,
                "album": album_name or album,
                "artist": track_artists[0] if track_artists else artist,
            }
            cache[key] = info
            return info
    except Exception as exc:
        logger.warning("TIDAL katalog araması başarısız: %s", exc)

    cache[key] = None
    return None


async def get_tidal_state():
    manager = await MediaManager.request_async()
    for session in manager.get_sessions():
        if "tidal" not in (session.source_app_user_model_id or "").lower():
            continue
        props = await session.try_get_media_properties_async()
        playback = session.get_playback_info()
        timeline = session.get_timeline_properties()

        playing = playback.playback_status == PLAYING
        position = timeline.position.total_seconds()
        if playing and timeline.last_updated_time:
            position += (datetime.now(timezone.utc) - timeline.last_updated_time).total_seconds()
        duration = (timeline.end_time - timeline.start_time).total_seconds()

        return {
            "title": props.title,
            "artist": props.artist,
            "album": props.album_title,
            "playing": playing,
            "pos": max(position, 0),
            "dur": duration,
        }
    return None


def build_activity(state: dict, info: dict | None) -> dict:
    now = time.time()
    duration = state["dur"]
    start = int(now - state["pos"])
    artist_name = str(state.get("artist") or "").strip()
    if not artist_name and info and info.get("artist"):
        artist_name = str(info["artist"]).strip()
    artist_name = artist_name or "TIDAL"
    album_name = (info["album"] if info else state["album"]) or ""
    activity = {
        "activity_type": ActivityType.LISTENING,
        "name": artist_name[:128],
        "details": state["title"][:128],
        "state": album_name[:128] or "Unknown",
        "large_text": album_name or state["title"],
        "start": start,
    }
    if duration:
        activity["end"] = int(start + duration)

    if info:
        if info.get("cover"):
            activity["large_image"] = info["cover"]
            activity["_urls"] = {"large_url": info["album_url"]}
        activity["buttons"] = [
            {"label": "TIDAL'da Dinle", "url": info["track_url"]},
            {"label": "Sanatçı", "url": info["artist_url"]},
        ]
    return activity


async def push(rpc: AioPresence, activity: dict):
    urls = activity.pop("_urls", {})
    try:
        await rpc.update(**activity, **urls)
    except TypeError:
        await rpc.update(**activity)


def make_tray_image() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((3, 3, 61, 61), radius=15, fill=(0, 169, 165, 255))
    # Simple white audio waveform, legible at notification-area icon size.
    for x, height in ((17, 14), (25, 27), (33, 20), (41, 31), (49, 12)):
        draw.rounded_rectangle(
            (x - 2, 32 - height // 2, x + 2, 32 + height // 2),
            radius=2,
            fill=(255, 255, 255, 255),
        )
    return image


def start_tray_icon(stop_event: asyncio.Event, loop: asyncio.AbstractEventLoop):
    def quit_from_tray(icon, _item):
        loop.call_soon_threadsafe(stop_event.set)
        icon.stop()

    icon = pystray.Icon(
        "tidal-rpc",
        make_tray_image(),
        "TIDAL Discord Rich Presence",
        menu=pystray.Menu(MenuItem("Çıkış", quit_from_tray)),
    )
    icon.run_detached()
    return icon


async def main():
    if not DISCORD_CLIENT_ID:
        logger.critical(".env dosyasında DISCORD_CLIENT_ID ayarlı değil; uygulama başlatılmadı.")
        return
    if not TIDAL_CLIENT_ID or not TIDAL_CLIENT_SECRET:
        logger.warning("TIDAL API bilgileri eksik; parça kapak ve bağlantı araması kapalı.")
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    tray_icon = start_tray_icon(stop_event, loop)
    rpc = AioPresence(DISCORD_CLIENT_ID)
    while not stop_event.is_set():
        try:
            await rpc.connect()
            break
        except Exception as exc:
            logger.info("Discord henüz hazır değil; 10 saniye sonra yeniden denenecek: %s", exc)
            await asyncio.sleep(10)
    logger.info("Discord'a bağlandı; TIDAL oturumu bekleniyor.")

    last_key = None
    last_sent = 0.0
    last_start = 0
    cleared = True

    while not stop_event.is_set():
        try:
            state = await get_tidal_state()
            if not state or not state["playing"] or not state["title"]:
                if not cleared:
                    await rpc.clear()
                    cleared = True
                    last_key = None
                await asyncio.sleep(POLL_SECONDS)
                continue

            key = (state["title"], state["artist"], state["album"])
            start = int(time.time() - state["pos"])
            changed = key != last_key or abs(start - last_start) > 3 or cleared

            if changed and time.time() - last_sent >= MIN_UPDATE_GAP:
                info = lookup(*key)
                await push(rpc, build_activity(state, info))
                last_key, last_start, last_sent, cleared = key, start, time.time(), False
                logger.info("Presence güncellendi: %s - %s", state["artist"], state["title"])

        except Exception as exc:
            logger.exception("Çalışma sırasında hata oluştu: %s", exc)
            try:
                await rpc.connect()
            except Exception:
                pass
            await asyncio.sleep(5)

        await asyncio.sleep(POLL_SECONDS)

    tray_icon.stop()
    try:
        await rpc.clear()
    except Exception:
        pass


if __name__ == "__main__":
    if not acquire_single_instance():
        logger.info("TIDAL RPC zaten çalışıyor; ikinci örnek başlatılmadı.")
        raise SystemExit(0)
    asyncio.run(main())
