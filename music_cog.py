import asyncio
import logging
import os
import shutil
import tempfile
import time
from typing import Any, Optional, Tuple

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from yt_dlp import YoutubeDL

from brand import (
    EMBED_ACCENT,
    FOOTER_DEFAULT,
    empty_embed,
    error_embed,
    info_embed,
    ok_embed,
    warn_embed,
)
from player_view import (
    BTN_STYLE,
    CID_LOOP,
    CID_PAUSE,
    NowPlayingView,
    QueuePanelView,
    build_now_playing_embed,
    build_queue_embed,
    playback_position_seconds,
)

load_dotenv()

log = logging.getLogger(__name__)

YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "noplaylist": True,
    "nocheckcertificate": True,
    "extractor_args": {
        "youtube": {"player_client": ["tv", "android", "web"]},
    },
}

YTDL_PLAYLIST_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "skip_download": True,
}

PLAYLIST_CAP = 50
QUEUE_PAGE_SIZE = 15


class music_cog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_settings: dict[int, dict[str, Any]] = {}
        self._guild_locks: dict[int, asyncio.Lock] = {}

    async def cog_load(self) -> None:
        # Persistent views: buttons keep working after restart.
        self.bot.add_view(NowPlayingView(self))
        self.bot.add_view(QueuePanelView(self))
        if not self.refresh_panels.is_running():
            self.refresh_panels.start()

    async def cog_unload(self) -> None:
        self.refresh_panels.cancel()

    def ensure_guild_settings(self, guild_id: int) -> dict[str, Any]:
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = {
                "is_playing": False,
                "is_paused": False,
                "is_looping": False,
                "current_song": None,
                "music_queue": [],
                "vc": None,
                "seek_position": 0,
                "playback_started_at": None,
                "ignore_after": False,
                "notify_channel_id": None,
                "panel_message_id": None,
                "panel_channel_id": None,
                "panel_mode": "now",
            }
        settings = self.guild_settings[guild_id]
        settings.setdefault("panel_message_id", None)
        settings.setdefault("panel_channel_id", None)
        settings.setdefault("playback_started_at", None)
        settings.setdefault("panel_mode", "now")
        return settings

    def _mark_playback_started(self, settings: dict[str, Any]) -> None:
        settings["playback_started_at"] = time.monotonic()

    def _freeze_playback_position(self, settings: dict[str, Any]) -> None:
        settings["seek_position"] = playback_position_seconds(settings)
        settings["playback_started_at"] = None

    def _guild_lock(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self._guild_locks:
            self._guild_locks[guild_id] = asyncio.Lock()
        return self._guild_locks[guild_id]

    def _remember_channel(self, ctx: commands.Context) -> None:
        settings = self.ensure_guild_settings(ctx.guild.id)
        settings["notify_channel_id"] = ctx.channel.id

    # —— Panel helpers ——

    def user_may_control(
        self, guild: discord.Guild, user: discord.abc.User
    ) -> bool:
        """Only members in the same voice channel as Benji may use panel buttons."""
        settings = self.ensure_guild_settings(guild.id)
        vc = settings.get("vc") or guild.voice_client
        if vc is None or not vc.is_connected() or vc.channel is None:
            return False
        member = guild.get_member(user.id)
        if member is None or member.voice is None or member.voice.channel is None:
            return False
        return member.voice.channel.id == vc.channel.id

    def _sync_button_styles(
        self, view: NowPlayingView, settings: dict[str, Any]
    ) -> None:
        """Labels only — Discord buttons can't use custom brand hex colors."""
        paused = bool(settings.get("is_paused"))
        looping = bool(settings.get("is_looping"))
        for child in view.children:
            if not isinstance(child, discord.ui.Button):
                continue
            child.style = BTN_STYLE
            if child.custom_id == CID_PAUSE:
                child.label = "Resume" if paused else "Pause"
                child.emoji = "▶️" if paused else "⏸️"
            elif child.custom_id == CID_LOOP:
                child.label = "Loop on" if looping else "Loop"

    async def upsert_panel(
        self, guild_id: int, *, force_now: bool = False
    ) -> None:
        """Edit the live Now Playing panel, or send a new one if missing."""
        settings = self.ensure_guild_settings(guild_id)
        if force_now:
            settings["panel_mode"] = "now"
        channel_id = settings.get("panel_channel_id") or settings.get(
            "notify_channel_id"
        )
        channel = self.bot.get_channel(channel_id or 0)
        if channel is None or not isinstance(channel, discord.abc.Messageable):
            return

        if settings.get("panel_mode") == "queue" and not force_now:
            # Keep queue view stable; only refresh its listing.
            embed = build_queue_embed(settings)
            view: discord.ui.View = QueuePanelView(self)
        else:
            thumb = None
            current = settings.get("current_song")
            if current:
                thumb = await self.get_thumbnail_url(current[0].get("id") or "")
            embed = build_now_playing_embed(settings, thumb_url=thumb)
            view = NowPlayingView(self)
            self._sync_button_styles(view, settings)

        msg_id = settings.get("panel_message_id")
        if msg_id and settings.get("panel_channel_id"):
            try:
                existing_channel = self.bot.get_channel(settings["panel_channel_id"])
                if existing_channel is not None:
                    msg = await existing_channel.fetch_message(msg_id)
                    await msg.edit(embed=embed, view=view)
                    self.bot.add_view(view, message_id=msg.id)
                    return
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                log.info("Panel message missing for guild %s; sending new", guild_id)

        try:
            settings["panel_mode"] = "now"
            thumb = None
            current = settings.get("current_song")
            if current:
                thumb = await self.get_thumbnail_url(current[0].get("id") or "")
            embed = build_now_playing_embed(settings, thumb_url=thumb)
            view = NowPlayingView(self)
            self._sync_button_styles(view, settings)
            msg = await channel.send(embed=embed, view=view)
            settings["panel_message_id"] = msg.id
            settings["panel_channel_id"] = channel.id
            self.bot.add_view(view, message_id=msg.id)
        except discord.HTTPException:
            log.exception("Failed to send Now Playing panel")

    @tasks.loop(seconds=15.0)
    async def refresh_panels(self) -> None:
        """Keep the progress bar roughly live while audio is playing."""
        for guild_id, settings in list(self.guild_settings.items()):
            if not settings.get("is_playing") or settings.get("is_paused"):
                continue
            if settings.get("panel_mode") == "queue":
                continue
            if not settings.get("panel_message_id"):
                continue
            try:
                await self.upsert_panel(guild_id)
            except Exception:
                log.exception("refresh_panels failed for guild %s", guild_id)

    @refresh_panels.before_loop
    async def _before_refresh_panels(self) -> None:
        await self.bot.wait_until_ready()

    async def panel_toggle_pause(self, guild_id: int) -> Tuple[bool, Optional[str]]:
        settings = self.ensure_guild_settings(guild_id)
        vc = settings.get("vc")
        if vc is None:
            return False, "Nothing is playing."
        if settings["is_playing"] and vc.is_playing():
            self._freeze_playback_position(settings)
            vc.pause()
            settings["is_playing"] = False
            settings["is_paused"] = True
            return True, None
        if settings["is_paused"] and vc.is_paused():
            vc.resume()
            settings["is_paused"] = False
            settings["is_playing"] = True
            self._mark_playback_started(settings)
            return True, None
        return False, "Nothing to pause or resume."

    async def panel_skip(self, guild_id: int) -> Tuple[bool, Optional[str]]:
        settings = self.ensure_guild_settings(guild_id)
        vc = settings.get("vc")
        if vc is None or (not vc.is_playing() and not vc.is_paused()):
            if settings["music_queue"]:
                await self.start_track(guild_id)
                return True, None
            return False, "Nothing to skip."
        # Stop without letting after-callback advance; we advance ourselves.
        settings["ignore_after"] = True
        vc.stop()
        await self.advance(guild_id)
        return True, None

    async def panel_seek(
        self, guild_id: int, seconds: int
    ) -> Tuple[bool, Optional[str]]:
        settings = self.ensure_guild_settings(guild_id)
        if settings["current_song"] is None or settings.get("vc") is None:
            return False, "No song is currently playing."
        path = settings.get("audio_path")
        if not path or not os.path.isfile(path):
            return False, "Could not seek — audio file missing."
        current_pos = playback_position_seconds(settings)
        settings["seek_position"] = max(0, current_pos + seconds)
        settings["playback_started_at"] = None
        vc = settings["vc"]
        try:
            settings["ignore_after"] = True
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            source = self._build_audio_source(path, seek=settings["seek_position"])
            vc.play(source, after=self._schedule_after(guild_id))
            settings["is_playing"] = True
            settings["is_paused"] = False
            self._mark_playback_started(settings)
            return True, None
        except Exception:
            log.exception("panel_seek failed")
            settings["ignore_after"] = False
            return False, "An error occurred while seeking."

    async def panel_toggle_loop(self, guild_id: int) -> Tuple[bool, Optional[str]]:
        settings = self.ensure_guild_settings(guild_id)
        if not (settings["is_playing"] or settings["is_paused"]):
            return False, "No song is currently being played."
        settings["is_looping"] = not settings["is_looping"]
        return True, None

    async def panel_stop(self, guild_id: int) -> None:
        settings = self.ensure_guild_settings(guild_id)
        settings["is_playing"] = False
        settings["is_paused"] = False
        settings["is_looping"] = False
        settings["music_queue"] = []
        settings["current_song"] = None
        settings["seek_position"] = 0
        settings["playback_started_at"] = None
        self._cleanup_audio_file(settings)
        vc = settings.get("vc")
        if vc is not None and vc.is_connected():
            settings["ignore_after"] = True
            try:
                if vc.is_playing() or vc.is_paused():
                    vc.stop()
            except Exception:
                pass
            try:
                await vc.disconnect()
            except Exception:
                log.exception("panel_stop disconnect failed")
        settings["vc"] = None

    # —— YouTube resolve (yt-dlp only) ——

    def _extract_info(self, query: str, *, playlist: bool = False) -> Any:
        opts = YTDL_PLAYLIST_OPTS if playlist else YTDL_OPTS
        with YoutubeDL(opts) as ytdl:
            return ytdl.extract_info(query, download=False)

    async def resolve_track(self, query: str) -> Optional[dict[str, str]]:
        query = (query or "").strip()
        if not query:
            return None
        try:
            target = query if query.startswith("http") else f"ytsearch1:{query}"
            info = await asyncio.to_thread(self._extract_info, target, playlist=False)
            if not info:
                return None
            if "entries" in info:
                entries = [e for e in (info.get("entries") or []) if e]
                if not entries:
                    return None
                info = entries[0]
            video_id = info.get("id")
            webpage = info.get("webpage_url") or info.get("url")
            if video_id and not webpage:
                webpage = f"https://www.youtube.com/watch?v={video_id}"
            title = info.get("title") or "Unknown title"
            if not webpage:
                return None
            duration = info.get("duration")
            track = {
                "source": webpage,
                "title": title,
                "id": str(video_id) if video_id else "",
            }
            if duration is not None:
                try:
                    track["duration"] = int(duration)
                except (TypeError, ValueError):
                    pass
            return track
        except Exception:
            log.exception("resolve_track failed for %r", query)
            return None

    async def resolve_playlist(self, playlist_url: str) -> list[dict[str, str]]:
        try:
            info = await asyncio.to_thread(
                self._extract_info, playlist_url, playlist=True
            )
            if not info:
                return []
            entries = info.get("entries") or []
            tracks: list[dict[str, str]] = []
            for entry in entries:
                if not entry:
                    continue
                video_id = entry.get("id")
                if not video_id:
                    continue
                title = entry.get("title") or f"Video {video_id}"
                url = entry.get("url") or entry.get("webpage_url")
                if url and not str(url).startswith("http"):
                    url = f"https://www.youtube.com/watch?v={video_id}"
                if not url:
                    url = f"https://www.youtube.com/watch?v={video_id}"
                track = {"source": url, "title": title, "id": str(video_id)}
                duration = entry.get("duration")
                if duration is not None:
                    try:
                        track["duration"] = int(duration)
                    except (TypeError, ValueError):
                        pass
                tracks.append(track)
                if len(tracks) >= PLAYLIST_CAP:
                    break
            return tracks
        except Exception:
            log.exception("resolve_playlist failed for %r", playlist_url)
            return []

    def _cleanup_audio_file(self, settings: dict[str, Any]) -> None:
        path = settings.pop("audio_path", None)
        tmpdir = settings.pop("audio_tmpdir", None)
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
        if tmpdir and os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _download_audio(self, page_url: str) -> Optional[dict[str, str]]:
        tmpdir = tempfile.mkdtemp(prefix="benji_yt_")
        outtmpl = os.path.join(tmpdir, "track.%(ext)s")
        opts = {
            **YTDL_OPTS,
            "outtmpl": outtmpl,
            "paths": {"home": tmpdir},
        }
        try:
            with YoutubeDL(opts) as ytdl:
                info = ytdl.extract_info(page_url, download=True)
                if "entries" in (info or {}):
                    entries = [e for e in (info.get("entries") or []) if e]
                    info = entries[0] if entries else None
                if not info:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    return None
                path = ytdl.prepare_filename(info)
                if not os.path.isfile(path):
                    for name in os.listdir(tmpdir):
                        candidate = os.path.join(tmpdir, name)
                        if os.path.isfile(candidate):
                            path = candidate
                            break
                if not os.path.isfile(path):
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    return None
                return {"path": path, "tmpdir": tmpdir}
        except Exception:
            log.exception("download_audio failed for %r", page_url)
            shutil.rmtree(tmpdir, ignore_errors=True)
            return None

    async def prepare_audio(self, page_url: str) -> Optional[dict[str, str]]:
        return await asyncio.to_thread(self._download_audio, page_url)

    def _build_audio_source(self, file_path: str, *, seek: int = 0):
        options = "-vn"
        if seek > 0:
            options = f"-vn -ss {seek}"
        return discord.FFmpegPCMAudio(file_path, options=options)

    async def get_thumbnail_url(self, video_id: str) -> Optional[str]:
        if not video_id:
            return None
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        def _fetch() -> Optional[str]:
            try:
                import googleapiclient.discovery

                youtube = googleapiclient.discovery.build(
                    "youtube", "v3", developerKey=api_key, cache_discovery=False
                )
                response = (
                    youtube.videos()
                    .list(part="snippet", id=video_id)
                    .execute()
                )
                items = response.get("items") or []
                if not items:
                    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                thumbs = items[0]["snippet"]["thumbnails"]
                for key in ("medium", "high", "default"):
                    if key in thumbs:
                        return thumbs[key]["url"]
            except Exception:
                log.exception("thumbnail API failed for %s", video_id)
            return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        return await asyncio.to_thread(_fetch)

    # —— Player core ——

    def _schedule_after(self, guild_id: int):
        def _after(error):
            if error:
                log.error("Player error in guild %s: %s", guild_id, error)
            fut = asyncio.run_coroutine_threadsafe(
                self._on_track_end(guild_id), self.bot.loop
            )
            try:
                fut.result(timeout=30)
            except Exception:
                log.exception("after-callback failed for guild %s", guild_id)

        return _after

    async def _on_track_end(self, guild_id: int) -> None:
        settings = self.ensure_guild_settings(guild_id)
        if settings.get("ignore_after"):
            settings["ignore_after"] = False
            return
        self._cleanup_audio_file(settings)
        await self.advance(guild_id)

    async def _ensure_voice(
        self,
        guild: discord.Guild,
        settings: dict[str, Any],
        voice_channel: discord.VoiceChannel,
    ) -> Optional[discord.VoiceClient]:
        vc = guild.voice_client or settings.get("vc")
        if vc is not None and vc.is_connected():
            settings["vc"] = vc
            if vc.channel and vc.channel.id == voice_channel.id:
                return vc
            try:
                await vc.move_to(voice_channel)
                return vc
            except Exception:
                log.exception("move_to failed; forcing reconnect")
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass
                await asyncio.sleep(1)

        if guild.voice_client is not None:
            try:
                await guild.voice_client.disconnect(force=True)
            except Exception:
                pass
            await asyncio.sleep(1)

        try:
            settings["vc"] = await voice_channel.connect(reconnect=True, timeout=90)
            log.info("Connected to voice channel %s", voice_channel.id)
            return settings["vc"]
        except discord.ClientException:
            vc = guild.voice_client
            if vc and vc.is_connected():
                settings["vc"] = vc
                return vc
            log.exception("Failed to connect to voice (ClientException)")
            return None
        except Exception:
            log.exception("Failed to connect to voice")
            return None

    async def start_track(self, guild_id: int) -> None:
        async with self._guild_lock(guild_id):
            await self._start_track_locked(guild_id)

    async def _start_track_locked(self, guild_id: int) -> None:
        settings = self.ensure_guild_settings(guild_id)
        guild = self.bot.get_guild(guild_id)

        if not settings["music_queue"]:
            settings["is_playing"] = False
            settings["is_paused"] = False
            settings["current_song"] = None
            settings["seek_position"] = 0
            settings["playback_started_at"] = None
            await self.upsert_panel(guild_id, force_now=True)
            return

        entry = settings["music_queue"].pop(0)
        song, voice_channel = entry[0], entry[1]
        settings["current_song"] = entry
        settings["seek_position"] = 0
        settings["playback_started_at"] = None
        settings["is_playing"] = True
        settings["is_paused"] = False

        channel = self.bot.get_channel(settings.get("notify_channel_id") or 0)

        if guild is None:
            settings["is_playing"] = False
            settings["music_queue"].insert(0, entry)
            return

        self._cleanup_audio_file(settings)
        audio = await self.prepare_audio(song["source"])
        if not audio:
            settings["is_playing"] = False
            if channel:
                await channel.send(
                    embed=error_embed(
                        f"Could not download **{song['title']}** — skipping."
                    )
                )
            await self._advance_locked(guild_id)
            return

        settings["audio_path"] = audio["path"]
        settings["audio_tmpdir"] = audio["tmpdir"]

        vc = await self._ensure_voice(guild, settings, voice_channel)
        if vc is None or not vc.is_connected():
            settings["is_playing"] = False
            settings["music_queue"].insert(0, entry)
            self._cleanup_audio_file(settings)
            if channel:
                await channel.send(
                    embed=error_embed(
                        "Could not connect to the voice channel.\n"
                        "Try `!stop` then `!play` again."
                    )
                )
            return

        await asyncio.sleep(0.5)
        if not vc.is_connected():
            settings["is_playing"] = False
            settings["music_queue"].insert(0, entry)
            self._cleanup_audio_file(settings)
            if channel:
                await channel.send(
                    embed=error_embed(
                        "Voice dropped before playback. Try `!play` again."
                    )
                )
            return

        try:
            if vc.is_playing() or vc.is_paused():
                settings["ignore_after"] = True
                vc.stop()
            source = self._build_audio_source(audio["path"])
            vc.play(source, after=self._schedule_after(guild_id))
            self._mark_playback_started(settings)
            log.info("Playing %s from %s", song["title"], audio["path"])
        except Exception:
            log.exception("start_track play failed")
            settings["is_playing"] = False
            self._cleanup_audio_file(settings)
            await self._advance_locked(guild_id)
            return

        await self.upsert_panel(guild_id, force_now=True)

    async def _advance_locked(self, guild_id: int) -> None:
        settings = self.ensure_guild_settings(guild_id)
        if settings.get("is_looping") and settings.get("current_song") is not None:
            # Replay the whole song from the start (ignore any seek offset).
            entry = settings["current_song"]
            settings["seek_position"] = 0
            settings["music_queue"].insert(0, entry)
        await self._start_track_locked(guild_id)

    async def advance(self, guild_id: int) -> None:
        settings = self.ensure_guild_settings(guild_id)
        if settings.get("is_looping") and settings.get("current_song") is not None:
            entry = settings["current_song"]
            settings["seek_position"] = 0
            settings["music_queue"].insert(0, entry)
        await self.start_track(guild_id)

    async def seek(self, ctx: commands.Context, seconds: int) -> None:
        guild_id = ctx.guild.id
        self._remember_channel(ctx)
        ok, err = await self.panel_seek(guild_id, seconds)
        if not ok:
            await ctx.send(embed=warn_embed(err or "Could not seek."))
            return
        await self.upsert_panel(guild_id)

    async def _queue_embed(self, song: dict[str, str], *, title: str) -> discord.Embed:
        thumb = await self.get_thumbnail_url(song.get("id") or "")
        embed = discord.Embed(
            title=title,
            description=f"[Open on YouTube]({song['source']})",
            color=EMBED_ACCENT,
        )
        if thumb:
            embed.set_thumbnail(url=thumb)
        embed.set_footer(text=f"Queued · {FOOTER_DEFAULT}")
        return embed

    # —— Commands ——

    @commands.command(name="play", aliases=["p", "playing"], help="Enqueue a YouTube song")
    async def play(self, ctx: commands.Context, *args):
        query = " ".join(args).strip()
        if not query:
            await ctx.send(
                embed=info_embed("Usage: `!play <search or YouTube URL>`")
            )
            return

        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send(
                embed=warn_embed("Join a voice channel first, then try again.")
            )
            return

        guild_id = ctx.guild.id
        settings = self.ensure_guild_settings(guild_id)
        self._remember_channel(ctx)
        voice_channel = ctx.author.voice.channel

        song = await self.resolve_track(query)
        if not song:
            await ctx.send(
                embed=error_embed(
                    "Could not find that track. Try another search or URL."
                )
            )
            return

        settings["music_queue"].append([song, voice_channel])
        should_start = not settings["is_playing"] and not settings["is_paused"]

        if should_start:
            await self.start_track(guild_id)
        else:
            await self.upsert_panel(guild_id)
            await ctx.send(
                embed=await self._queue_embed(
                    song, title=f"Queued: {song['title']}"
                )
            )

    @commands.command(name="ff", help="Fast-forward 10 seconds")
    async def fast_forward(self, ctx: commands.Context):
        await self.seek(ctx, 10)

    @commands.command(name="rw", help="Rewind 10 seconds")
    async def rewind(self, ctx: commands.Context):
        await self.seek(ctx, -10)

    @commands.command(name="playlist", help="Enqueue a YouTube playlist (max 50)")
    async def add_playlist_to_queue(self, ctx: commands.Context, playlist_url: str):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send(
                embed=warn_embed("Join a voice channel first, then try again.")
            )
            return

        guild_id = ctx.guild.id
        settings = self.ensure_guild_settings(guild_id)
        self._remember_channel(ctx)
        voice_channel = ctx.author.voice.channel

        await ctx.send(embed=info_embed("Loading playlist…"))
        tracks = await self.resolve_playlist(playlist_url)
        if not tracks:
            await ctx.send(
                embed=error_embed(
                    "No valid videos found (or the playlist could not be read).",
                    title="Playlist error",
                )
            )
            return

        for track in tracks:
            settings["music_queue"].append([track, voice_channel])

        should_start = not settings["is_playing"] and not settings["is_paused"]
        if should_start:
            await self.start_track(guild_id)
        else:
            await self.upsert_panel(guild_id)
            await ctx.send(
                embed=ok_embed(
                    f"Added **{len(tracks)}** track(s) (cap {PLAYLIST_CAP}).",
                    title="Playlist queued",
                )
            )

    @commands.command(name="pause", help="Pause or resume the current song")
    async def pause(self, ctx: commands.Context):
        ok, err = await self.panel_toggle_pause(ctx.guild.id)
        if not ok:
            await ctx.send(embed=warn_embed(err or "Nothing to pause."))
            return
        await self.upsert_panel(ctx.guild.id)

    @commands.command(name="resume", aliases=["r"], help="Resume playback")
    async def resume(self, ctx: commands.Context):
        settings = self.ensure_guild_settings(ctx.guild.id)
        if not settings["is_paused"]:
            await ctx.send(embed=warn_embed("Nothing is paused."))
            return
        ok, err = await self.panel_toggle_pause(ctx.guild.id)
        if not ok:
            await ctx.send(embed=warn_embed(err or "Nothing is paused."))
            return
        await self.upsert_panel(ctx.guild.id)

    @commands.command(name="skip", aliases=["s"], help="Skip the current song")
    async def skip(self, ctx: commands.Context):
        self._remember_channel(ctx)
        ok, err = await self.panel_skip(ctx.guild.id)
        if not ok:
            await ctx.send(embed=warn_embed(err or "Nothing to skip."))
            return
        await self.upsert_panel(ctx.guild.id)

    @commands.command(name="queue", aliases=["q"], help="Show the queue")
    async def queue(self, ctx: commands.Context):
        settings = self.ensure_guild_settings(ctx.guild.id)
        if not settings["music_queue"] and not settings.get("current_song"):
            await ctx.send(embed=empty_embed("Queue is empty — use `!play` to add a track."))
            return
        embed = build_queue_embed(settings)
        # Paginate by truncating description if somehow huge (panel helper already caps).
        if len(settings["music_queue"]) > QUEUE_PAGE_SIZE:
            embed.set_footer(
                text=f"{FOOTER_DEFAULT}  ·  showing full list (cap {QUEUE_PAGE_SIZE}+)"
            )
        await ctx.send(embed=embed)

    @commands.command(name="clear", aliases=["c", "bin"], help="Clear the queue")
    async def clear(self, ctx: commands.Context):
        settings = self.ensure_guild_settings(ctx.guild.id)
        settings["music_queue"] = []
        settings["is_looping"] = False
        vc = settings.get("vc")
        if vc is not None and (vc.is_playing() or vc.is_paused()):
            settings["ignore_after"] = True
            vc.stop()
        settings["is_playing"] = False
        settings["is_paused"] = False
        settings["current_song"] = None
        await self.upsert_panel(ctx.guild.id)
        await ctx.send(embed=ok_embed("Music queue cleared."))

    @commands.command(
        name="stop", aliases=["disconnect", "l", "d"], help="Leave the voice channel"
    )
    async def dc(self, ctx: commands.Context):
        settings = self.ensure_guild_settings(ctx.guild.id)
        was_connected = settings.get("vc") is not None and (
            settings["vc"].is_connected() if settings.get("vc") else False
        )
        await self.panel_stop(ctx.guild.id)
        await self.upsert_panel(ctx.guild.id)
        if not was_connected:
            await ctx.send(embed=warn_embed("Not connected to a voice channel."))
        else:
            await ctx.send(embed=ok_embed("Disconnected."))

    @commands.command(name="remove", aliases=["rm"], help="Remove the last queued song")
    async def remove(self, ctx: commands.Context):
        settings = self.ensure_guild_settings(ctx.guild.id)
        if not settings["music_queue"]:
            await ctx.send(embed=empty_embed("The queue is empty."))
            return
        removed = settings["music_queue"].pop()
        await self.upsert_panel(ctx.guild.id)
        await ctx.send(
            embed=warn_embed(f"Removed **{removed[0]['title']}** from the queue.")
        )

    @commands.command(name="removeat", aliases=["rmat"], help="Remove song at position")
    async def remove_at(self, ctx: commands.Context, position: int):
        settings = self.ensure_guild_settings(ctx.guild.id)
        if 0 < position <= len(settings["music_queue"]):
            removed = settings["music_queue"].pop(position - 1)
            await self.upsert_panel(ctx.guild.id)
            await ctx.send(
                embed=warn_embed(
                    f"Removed **{removed[0]['title']}** from position {position}."
                )
            )
        else:
            await ctx.send(
                embed=error_embed(
                    f"Invalid position. Queue has {len(settings['music_queue'])} song(s)."
                )
            )

    @commands.command(
        name="removemultiple",
        aliases=["rmulti", "rmm"],
        help="Remove songs at positions",
    )
    async def remove_multiple(self, ctx: commands.Context, *positions: int):
        settings = self.ensure_guild_settings(ctx.guild.id)
        if not positions:
            await ctx.send(
                embed=info_embed("Specify one or more queue positions to remove.")
            )
            return
        removed_titles = []
        for position in sorted(set(positions), reverse=True):
            if 0 < position <= len(settings["music_queue"]):
                removed_titles.append(
                    settings["music_queue"].pop(position - 1)[0]["title"]
                )
        if removed_titles:
            await self.upsert_panel(ctx.guild.id)
            await ctx.send(
                embed=warn_embed(
                    "Removed:\n" + "\n".join(f"• {t}" for t in removed_titles)
                )
            )
        else:
            await ctx.send(
                embed=warn_embed("No songs removed — check the positions.")
            )

    @commands.command(name="add", aliases=["a"], help="Insert a song at a queue position")
    async def add_song(self, ctx: commands.Context, position: int, *args):
        query = " ".join(args).strip()
        if not query:
            await ctx.send(
                embed=info_embed("Usage: `!add <position> <search or URL>`")
            )
            return
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send(
                embed=warn_embed("Join a voice channel first, then try again.")
            )
            return

        settings = self.ensure_guild_settings(ctx.guild.id)
        self._remember_channel(ctx)
        if position < 1 or position > len(settings["music_queue"]) + 1:
            await ctx.send(
                embed=error_embed("Invalid position — use 1 through queue length + 1.")
            )
            return

        song = await self.resolve_track(query)
        if not song:
            await ctx.send(embed=error_embed("Could not find that track."))
            return

        settings["music_queue"].insert(position - 1, [song, ctx.author.voice.channel])
        await self.upsert_panel(ctx.guild.id)

    @commands.command(name="swap", help="Swap two queue positions")
    async def swap_songs(self, ctx: commands.Context, position1: int, position2: int):
        settings = self.ensure_guild_settings(ctx.guild.id)
        q = settings["music_queue"]
        if not (1 <= position1 <= len(q) and 1 <= position2 <= len(q)):
            await ctx.send(embed=error_embed("Invalid positions."))
            return
        q[position1 - 1], q[position2 - 1] = q[position2 - 1], q[position1 - 1]
        await self.upsert_panel(ctx.guild.id)

    @commands.command(name="loop", help="Loop the current song")
    async def loop(self, ctx: commands.Context):
        settings = self.ensure_guild_settings(ctx.guild.id)
        if settings["is_playing"] or settings["is_paused"]:
            settings["is_looping"] = True
            await self.upsert_panel(ctx.guild.id)
        else:
            await ctx.send(embed=warn_embed("No song is currently being played."))

    @commands.command(name="unloop", help="Stop looping")
    async def unloop(self, ctx: commands.Context):
        settings = self.ensure_guild_settings(ctx.guild.id)
        if settings["is_looping"]:
            settings["is_looping"] = False
            await self.upsert_panel(ctx.guild.id)
        else:
            await ctx.send(embed=warn_embed("Looping is not enabled."))
