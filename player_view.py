"""Interactive Now Playing panel (buttons + editable embed)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Optional

import discord

from brand import EMBED_PRIMARY, FOOTER_DEFAULT, empty_embed, error_embed

if TYPE_CHECKING:
    from music_cog import music_cog

log = logging.getLogger(__name__)

# Persistent custom IDs (survive bot restart when view is re-added)
CID_RW = "benji:rw"
CID_PAUSE = "benji:pause"
CID_SKIP = "benji:skip"
CID_FF = "benji:ff"
CID_LOOP = "benji:loop"
CID_STOP = "benji:stop"
CID_QUEUE = "benji:queue"
CID_BACK = "benji:back"

# Discord cannot use custom hex colors on buttons — one shared style for branding consistency.
BTN_STYLE = discord.ButtonStyle.secondary


def format_timestamp(seconds: int | float | None) -> str:
    if seconds is None:
        return "?:??"
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def playback_position_seconds(settings: dict[str, Any]) -> int:
    """Elapsed seconds in the current track (accounts for seek + pause)."""
    base = int(settings.get("seek_position") or 0)
    if settings.get("is_paused") or not settings.get("is_playing"):
        return base
    started = settings.get("playback_started_at")
    if not started:
        return base
    return max(0, base + int(time.monotonic() - float(started)))


def progress_bar(position: int, duration: Optional[int], *, width: int = 12) -> str:
    if not duration or duration <= 0:
        return "░" * width
    ratio = min(1.0, max(0.0, position / duration))
    filled = int(round(ratio * width))
    return "█" * filled + "░" * (width - filled)


def format_progress_line(settings: dict[str, Any]) -> str:
    song = (settings.get("current_song") or [None])[0] or {}
    position = playback_position_seconds(settings)
    duration_raw = song.get("duration")
    try:
        duration = int(duration_raw) if duration_raw not in (None, "") else None
    except (TypeError, ValueError):
        duration = None
    if duration is not None and position > duration:
        position = duration
    bar = progress_bar(position, duration)
    left = format_timestamp(position)
    right = format_timestamp(duration)
    return f"`{bar}`\n**{left}** / **{right}**"


def build_now_playing_embed(
    settings: dict[str, Any],
    *,
    thumb_url: Optional[str] = None,
) -> discord.Embed:
    current = settings.get("current_song")
    if not current:
        return empty_embed("Nothing playing.", title="Now playing")

    song = current[0]
    paused = bool(settings.get("is_paused"))
    looping = bool(settings.get("is_looping"))

    title = "Paused" if paused else "Now playing"
    status_bits = ["Paused" if paused else "Playing"]
    if looping:
        status_bits.append("Looping this song")
    status_line = " · ".join(status_bits)

    up_next = settings.get("music_queue") or []
    if up_next:
        preview_parts = []
        for i, entry in enumerate(up_next[:3], start=1):
            preview_parts.append(f"**{i}.**  {entry[0]['title']}")
        preview = "\n\n".join(preview_parts)
        if len(up_next) > 3:
            preview += f"\n\n_…and {len(up_next) - 3} more_"
    else:
        preview = "_Queue empty_"

    # Discord markdown headings read larger than body text in embeds.
    embed = discord.Embed(
        title=title,
        description=(
            f"# {song['title']}\n\n"
            f"[Open on YouTube]({song['source']})\n\n"
            f"{format_progress_line(settings)}\n\n"
            f"{status_line}"
        ),
        color=EMBED_PRIMARY,
    )
    if thumb_url:
        embed.set_thumbnail(url=thumb_url)
    embed.add_field(name="Up next", value=preview, inline=False)
    embed.set_footer(text=FOOTER_DEFAULT)
    return embed


def build_queue_embed(settings: dict[str, Any]) -> discord.Embed:
    current = settings.get("current_song")
    queue = settings.get("music_queue") or []
    if not current and not queue:
        return empty_embed("Queue is empty.", title="Queue")

    blocks: list[str] = []
    if current:
        song = current[0]
        blocks.append(
            f"# Now playing\n\n"
            f"**{song['title']}**\n"
            f"[Open on YouTube]({song['source']})"
        )

    if queue:
        lines = ["# Up next\n"]
        for i, entry in enumerate(queue, start=1):
            song = entry[0]
            dur = song.get("duration")
            dur_bit = f"  ·  `{format_timestamp(dur)}`" if dur not in (None, "") else ""
            lines.append(
                f"## {i}\n"
                f"**{song['title']}**{dur_bit}\n"
                f"[Open on YouTube]({song['source']})"
            )
        blocks.append("\n\n".join(lines))

    text = "\n\n————————————\n\n".join(blocks)
    if len(text) > 3900:
        text = text[:3900] + "\n…"
    return discord.Embed(title="Queue", description=text, color=EMBED_PRIMARY).set_footer(
        text=FOOTER_DEFAULT
    )


class NowPlayingView(discord.ui.View):
    """Persistent control panel. Uses interaction.guild_id; cog resolved at click time."""

    def __init__(self, cog: Optional["music_cog"] = None):
        super().__init__(timeout=None)
        self.cog = cog

    def _get_cog(self, interaction: discord.Interaction) -> Optional["music_cog"]:
        if self.cog is not None:
            return self.cog
        return interaction.client.get_cog("music_cog")  # type: ignore[return-value]

    async def _deny(self, interaction: discord.Interaction, message: str) -> None:
        embed = error_embed(message)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        cog = self._get_cog(interaction)
        if cog is None or interaction.guild is None or interaction.user is None:
            await self._deny(interaction, "Bot is not ready.")
            return False
        if not cog.user_may_control(interaction.guild, interaction.user):
            await self._deny(
                interaction,
                "Join Benji’s voice channel to use these controls.",
            )
            return False
        return True

    async def _edit_panel(
        self, interaction: discord.Interaction, cog: "music_cog"
    ) -> None:
        """Rebuild embed+buttons after a control click.

        Named _edit_panel (not _refresh) — discord.ui.View already owns _refresh.
        """
        guild_id = interaction.guild_id
        assert guild_id is not None
        settings = cog.ensure_guild_settings(guild_id)
        thumb = None
        if settings.get("current_song"):
            song = settings["current_song"][0]
            thumb = await cog.get_thumbnail_url(song.get("id") or "")
        embed = build_now_playing_embed(settings, thumb_url=thumb)
        view = NowPlayingView(cog)
        cog._sync_button_styles(view, settings)
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.edit_message(embed=embed, view=view)
        if interaction.message:
            cog.bot.add_view(view, message_id=interaction.message.id)

    @discord.ui.button(
        label="Rewind",
        emoji="⏪",
        style=BTN_STYLE,
        custom_id=CID_RW,
        row=0,
    )
    async def btn_rw(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        cog = self._get_cog(interaction)
        assert cog and interaction.guild_id
        ok, err = await cog.panel_seek(interaction.guild_id, -10)
        if not ok:
            await self._deny(interaction, err or "Could not rewind.")
            return
        await self._edit_panel(interaction, cog)

    @discord.ui.button(
        label="Pause",
        emoji="⏸️",
        style=BTN_STYLE,
        custom_id=CID_PAUSE,
        row=0,
    )
    async def btn_pause(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        cog = self._get_cog(interaction)
        assert cog and interaction.guild_id
        ok, err = await cog.panel_toggle_pause(interaction.guild_id)
        if not ok:
            await self._deny(interaction, err or "Nothing to pause.")
            return
        await self._edit_panel(interaction, cog)

    @discord.ui.button(
        label="Skip",
        emoji="⏭️",
        style=BTN_STYLE,
        custom_id=CID_SKIP,
        row=0,
    )
    async def btn_skip(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        cog = self._get_cog(interaction)
        assert cog and interaction.guild_id
        await interaction.response.defer()
        ok, err = await cog.panel_skip(interaction.guild_id)
        if not ok:
            await interaction.followup.send(
                embed=error_embed(err or "Nothing to skip."), ephemeral=True
            )
            return
        await self._edit_panel(interaction, cog)

    @discord.ui.button(
        label="Forward",
        emoji="⏩",
        style=BTN_STYLE,
        custom_id=CID_FF,
        row=0,
    )
    async def btn_ff(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        cog = self._get_cog(interaction)
        assert cog and interaction.guild_id
        ok, err = await cog.panel_seek(interaction.guild_id, 10)
        if not ok:
            await self._deny(interaction, err or "Could not fast-forward.")
            return
        await self._edit_panel(interaction, cog)

    @discord.ui.button(
        label="Loop",
        emoji="🔁",
        style=BTN_STYLE,
        custom_id=CID_LOOP,
        row=1,
    )
    async def btn_loop(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        cog = self._get_cog(interaction)
        assert cog and interaction.guild_id
        ok, err = await cog.panel_toggle_loop(interaction.guild_id)
        if not ok:
            await self._deny(interaction, err or "Nothing playing.")
            return
        await self._edit_panel(interaction, cog)

    @discord.ui.button(
        label="Stop",
        emoji="⏹️",
        style=BTN_STYLE,
        custom_id=CID_STOP,
        row=1,
    )
    async def btn_stop(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        cog = self._get_cog(interaction)
        assert cog and interaction.guild_id
        await cog.panel_stop(interaction.guild_id)
        embed = empty_embed("Playback stopped.", title="Stopped")
        view = NowPlayingView(cog)
        for child in view.children:
            if isinstance(child, discord.ui.Button) and child.custom_id != CID_QUEUE:
                child.disabled = True
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(
        label="Queue",
        emoji="📜",
        style=BTN_STYLE,
        custom_id=CID_QUEUE,
        row=1,
    )
    async def btn_queue(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Swap the panel into a lasting Queue view (not ephemeral)."""
        cog = self._get_cog(interaction)
        assert cog and interaction.guild_id
        settings = cog.ensure_guild_settings(interaction.guild_id)
        settings["panel_mode"] = "queue"
        embed = build_queue_embed(settings)
        view = QueuePanelView(cog)
        await interaction.response.edit_message(embed=embed, view=view)
        if interaction.message:
            cog.bot.add_view(view, message_id=interaction.message.id)


class QueuePanelView(discord.ui.View):
    """Queue listing on the same panel message — stays visible until Back."""

    def __init__(self, cog: Optional["music_cog"] = None):
        super().__init__(timeout=None)
        self.cog = cog

    def _get_cog(self, interaction: discord.Interaction) -> Optional["music_cog"]:
        if self.cog is not None:
            return self.cog
        return interaction.client.get_cog("music_cog")  # type: ignore[return-value]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        cog = self._get_cog(interaction)
        if cog is None or interaction.guild is None or interaction.user is None:
            embed = error_embed("Bot is not ready.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        if not cog.user_may_control(interaction.guild, interaction.user):
            await interaction.response.send_message(
                embed=error_embed("Join Benji’s voice channel to use these controls."),
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Back",
        emoji="↩️",
        style=BTN_STYLE,
        custom_id=CID_BACK,
        row=0,
    )
    async def btn_back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        cog = self._get_cog(interaction)
        assert cog and interaction.guild_id
        settings = cog.ensure_guild_settings(interaction.guild_id)
        settings["panel_mode"] = "now"
        thumb = None
        if settings.get("current_song"):
            thumb = await cog.get_thumbnail_url(
                settings["current_song"][0].get("id") or ""
            )
        embed = build_now_playing_embed(settings, thumb_url=thumb)
        view = NowPlayingView(cog)
        cog._sync_button_styles(view, settings)
        await interaction.response.edit_message(embed=embed, view=view)
        if interaction.message:
            cog.bot.add_view(view, message_id=interaction.message.id)
