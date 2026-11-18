"""Per-guild saved playlists (local JSON)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "playlists")
NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")


def _path(guild_id: int) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, f"{guild_id}.json")


def normalize_name(name: str) -> str | None:
    name = (name or "").strip()
    if not NAME_RE.match(name):
        return None
    return name.lower()


def load_all(guild_id: int) -> dict[str, list[dict[str, Any]]]:
    path = _path(guild_id)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(k): v for k, v in data.items() if isinstance(v, list)}
    except (OSError, json.JSONDecodeError):
        return {}


def save_all(guild_id: int, data: dict[str, list[dict[str, Any]]]) -> None:
    path = _path(guild_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_names(guild_id: int) -> list[str]:
    return sorted(load_all(guild_id).keys())


def save_playlist(
    guild_id: int, name: str, tracks: list[dict[str, Any]]
) -> tuple[bool, str]:
    key = normalize_name(name)
    if not key:
        return False, "Name must be 1–32 chars: letters, numbers, `_` or `-`."
    data = load_all(guild_id)
    data[key] = tracks
    save_all(guild_id, data)
    return True, key


def load_playlist(guild_id: int, name: str) -> tuple[list[dict[str, Any]] | None, str]:
    key = normalize_name(name)
    if not key:
        return None, "Invalid playlist name."
    data = load_all(guild_id)
    if key not in data:
        return None, f"No playlist named `{key}`."
    return data[key], key


def delete_playlist(guild_id: int, name: str) -> tuple[bool, str]:
    key = normalize_name(name)
    if not key:
        return False, "Invalid playlist name."
    data = load_all(guild_id)
    if key not in data:
        return False, f"No playlist named `{key}`."
    del data[key]
    save_all(guild_id, data)
    return True, key
