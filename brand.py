"""Brand tokens + embed helpers for Benji (visual palette only)."""

from __future__ import annotations

import discord

# 60-30-10 palette
CREAM = discord.Color.from_rgb(0xF4, 0xEF, 0xE6)  # #F4EFE6
CANOPY = discord.Color.from_rgb(0x1E, 0x4D, 0x3B)  # #1E4D3B
AMBER = discord.Color.from_rgb(0xF5, 0xA6, 0x23)  # #F5A623

EMBED_PRIMARY = CANOPY
EMBED_ACCENT = AMBER
EMBED_OK = discord.Color.from_rgb(0x2F, 0x6B, 0x52)
EMBED_WARN = AMBER
EMBED_ERROR = discord.Color.from_rgb(0xB5, 0x4A, 0x3A)
EMBED_MUTED = discord.Color.from_rgb(0x6B, 0x7A, 0x70)

BRAND_NAME = "Benji"
BRAND_TAGLINE = "YouTube music in your voice channel"
FOOTER_DEFAULT = "Benji · YouTube"


def brand_embed(
    description: str,
    *,
    title: str | None = None,
    color: discord.Color = EMBED_PRIMARY,
    footer: str | None = FOOTER_DEFAULT,
) -> discord.Embed:
    embed = discord.Embed(description=description, color=color)
    if title:
        embed.title = title
    if footer:
        embed.set_footer(text=footer)
    return embed


def ok_embed(description: str, *, title: str | None = None) -> discord.Embed:
    return brand_embed(description, title=title, color=EMBED_OK)


def accent_embed(description: str, *, title: str | None = None) -> discord.Embed:
    return brand_embed(description, title=title, color=EMBED_ACCENT)


def warn_embed(description: str, *, title: str | None = None) -> discord.Embed:
    return brand_embed(description, title=title, color=EMBED_WARN)


def error_embed(description: str, *, title: str | None = None) -> discord.Embed:
    return brand_embed(description, title=title, color=EMBED_ERROR)


def info_embed(description: str, *, title: str | None = None) -> discord.Embed:
    return brand_embed(description, title=title, color=EMBED_PRIMARY)


def empty_embed(description: str, *, title: str | None = None) -> discord.Embed:
    return brand_embed(description, title=title, color=EMBED_MUTED)
