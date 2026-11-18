# Benji — Discord Music Bot

Personal Discord bot for playing music in voice channels, with an interactive Now Playing panel and YouTube playback via **yt-dlp**.

**Brand:** warm sand `#F4EFE6` · deep canopy `#1E4D3B` · solar amber `#F5A623`  
Avatar + banner live in [`branding/`](branding/) — upload them in the Discord Developer Portal (see that folder’s README).

## Features

- Interactive **Now Playing** panel (pause, skip, seek, loop, volume, queue)
- YouTube search with a **result picker** (or paste a URL to play directly)
- Queue management (add, remove, swap, clear)
- **Saved playlists** per server (`!save` / `!load`)
- YouTube playlist import (up to 50 tracks)
- Progress bar + elapsed / duration
- Volume 0–200% (panel buttons or `!vol`)
- Auto-leave VC after 5 minutes alone or fully idle
- Custom help + prefix

## Tech stack

- Python 3.10+
- discord.py (voice)
- yt-dlp
- FFmpeg
- Optional: YouTube Data API (thumbnails; falls back to `i.ytimg.com`)

## Setup

1. Clone and enter the project:

```bash
git clone https://github.com/SatyanThayaparan/discord-music-bot.git
cd discord-music-bot
```

2. Install [FFmpeg](https://ffmpeg.org/download.html) and add it to `PATH`.
3. Create a Discord application/bot at the [Developer Portal](https://developers.discord.com/applications):
   - Enable **Message Content** intent (Members/Presence optional)
   - Invite with Connect, Speak, Send Messages, Embed Links
4. Copy env template:

```bash
copy .env.example .env
```

```env
TOKEN=your_discord_bot_token
YOUTUBE_API_KEY=your_youtube_api_key
# Optional — only for cloud hosts that hit YouTube bot-checks:
# YTDLP_COOKIES=/path/to/cookies.txt
```

5. Run (creates `.venv` and installs [`requirements.txt`](requirements.txt) on first launch):

```powershell
.\run.ps1
```

## Fast deploy loop (dev)

Save a `.py` file and the bot restarts:

```powershell
.\dev.ps1
```

Smoke-test in a private server using [`test_inputs.txt`](test_inputs.txt).

## Usage

Default prefix: `!`

### Playback

| Command | Description |
|---------|-------------|
| `!play` / `!p <query>` | Search YouTube — pick from top results |
| `!play` / `!p <url>` | Play / enqueue a YouTube URL |
| `!pause` / `!resume` | Pause or resume |
| `!skip` / `!s` | Skip current track |
| `!ff` / `!rw` | Seek ±10 seconds |
| `!volume` / `!vol [0–200]` | Show or set volume |
| `!loop` / `!unloop` | Loop current song |
| `!stop` | Disconnect from voice |

### Queue & playlists

| Command | Description |
|---------|-------------|
| `!queue` / `!q` | Show queue |
| `!playlist <url>` | Enqueue a YouTube playlist (max 50) |
| `!save <name>` | Save now-playing + queue as a named playlist |
| `!load <name>` | Load a saved playlist into the queue |
| `!playlists` / `!pls` | List saved playlists |
| `!delplaylist <name>` | Delete a saved playlist |
| `!clear` | Clear queue and stop |
| `!remove` / `!rm` | Remove last queued song |
| `!removeat` / `!rmat <n>` | Remove at position |
| `!add` / `!a <n> <query>` | Insert at position |
| `!swap <a> <b>` | Swap two positions |

### Panel buttons

On the Now Playing message: Rewind · Pause/Resume · Skip · Forward · Vol − · Vol + · Loop · Stop · Queue (with Back).

Benji leaves the voice channel after **5 minutes** alone, or when fully idle (nothing playing and empty queue).

## Project structure

```text
discord-music-bot/
├── main.py              # entrypoint
├── music_cog.py         # playback, queue, YouTube, idle/volume
├── player_view.py       # Now Playing buttons + search select
├── playlists_store.py   # saved playlists (data/playlists/)
├── help_cog.py          # help + prefix
├── brand.py             # colors + embed helpers
├── branding/            # avatar + banner assets
├── requirements.txt
├── run.ps1              # single-instance start
├── dev.ps1              # auto-restart on .py changes
├── test_inputs.txt
├── .env.example
└── .env                 # local secrets (gitignored)
```

## Notes

- Secrets stay in `.env` only; saved playlists live under `data/playlists/` (gitignored JSON).
- FFmpeg is required for audio.
- Prefer running locally (home IP). Cloud hosts often need `YTDLP_COOKIES` because YouTube blocks datacenter IPs.
- Playback uses a single advance path so skip/seek do not double-fire the next track.
