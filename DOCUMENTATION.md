# Discord Music Bot — Documentation

## What this project is

A Discord bot that joins a voice channel and plays YouTube audio. Users can queue songs, pause/resume, skip, loop, and play playlists using chat commands.

## Tech stack

| Layer | Choice | Why it’s used |
| --- | --- | --- |
| Runtime | Python 3 | Bot logic and command handling |
| Discord API | discord.py | Connect to Discord, listen for commands, manage voice |
| Audio source | yt-dlp + YoutubeSearch | Resolve YouTube links/search queries into playable streams |
| Playback | FFmpeg | Decode/stream audio into Discord voice |
| Config | python-dotenv (`.env`) | Keep bot token and optional YouTube API key out of source |
| Optional | YouTube Data API | Extra metadata such as thumbnails when a key is set |

## How the logic works

1. **Startup** — `main.py` starts the Discord client and loads command modules (“cogs”), mainly the music cog and a help cog.
2. **Command intake** — Someone runs a command like play in a text channel. The music cog checks that a voice channel is available and that a song/URL/search term was provided.
3. **Resolve the track** — The bot turns a URL or search phrase into a streamable audio source using yt-dlp / search helpers.
4. **Queue per server** — Each Discord server (guild) keeps its own queue and playback state so two servers don’t interfere with each other.
5. **Voice playback** — The bot joins the user’s voice channel and feeds audio through FFmpeg. When a track ends, it automatically starts the next queued item.
6. **Controls** — Pause, resume, skip, loop, and related commands update that same per-server queue/player state.

## Project map

This bot is flat (no deep folders)—each Python file is a clear responsibility.

| Path | Role |
| --- | --- |
| `main.py` | Starts the Discord client, sets intents, and loads the music/help cogs |
| `music_cog.py` | Core product logic: search/resolve tracks, per-server queues, voice join, FFmpeg playback, pause/skip/loop-style controls |
| `help_cog.py` | Custom help command so users can see what the bot supports |
| `test_inputs.txt` | Scratch/notes for sample inputs while testing commands |
| `.env.example` | Template for `TOKEN` and optional `YOUTUBE_API_KEY` (copy to `.env`) |
| `.env` | Local secrets (gitignored)—never commit this |
| `README.md` | How to install dependencies, set the token, and run the bot |
| `DOCUMENTATION.md` | This overview |

### How the files talk to each other
`main.py` is the ignition key. Once running, Discord message events are handled by the loaded cogs—almost all day-to-day behavior lives in `music_cog.py`.

## Mental model

This is a **remote DJ for Discord**: chat commands decide what to play, a per-server queue remembers order, and FFmpeg is the speaker cable into the voice channel. There is no database—state lives in memory while the bot is running.
