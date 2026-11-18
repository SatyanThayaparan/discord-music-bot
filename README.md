# Benji — Solarpunk Discord Music Bot

Personal Discord bot for playing music in voice channels, with queue controls and YouTube playback via **yt-dlp**.

**Brand:** warm sand `#F4EFE6` · deep canopy `#1E4D3B` · solar amber `#F5A623`  
Avatar + banner live in [`branding/`](branding/) — upload them in the Discord Developer Portal (see that folder’s README).

## Features

- Play songs from YouTube search or links
- Queue management (add, remove, swap, clear, paginated `!queue`)
- Pause, resume, skip, loop
- Playlist import (up to 50 tracks)
- Fast-forward / rewind (10 seconds)
- Now-playing embeds
- Custom help command

## Tech stack

- Python 3.10+
- discord.py
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
   - Invite with connect, speak, and send-messages permissions
4. Copy env template:

```bash
copy .env.example .env
```

```env
TOKEN=your_discord_bot_token
YOUTUBE_API_KEY=your_youtube_api_key
```

5. Run (creates `.venv` and installs [`requirements.txt`](requirements.txt) on first launch):

```powershell
.\run.ps1
```

## Fast deploy loop (dev)

Like reloading a Chrome extension — save a `.py` file and the bot restarts:

```powershell
.\dev.ps1
```

Then smoke-test in a private Discord server using [`test_inputs.txt`](test_inputs.txt):

1. `!p <song>` — audio starts  
2. `!skip` — advances once  
3. `!ff` / `!rw` — seek without skipping the track  
4. `!q` / `!clear` / `!stop` — no crash  

## Usage

Default prefix: `!`

| Command | Description |
|---------|-------------|
| `!play` / `!p <query or url>` | Enqueue a track (starts if idle) |
| `!pause` / `!resume` | Pause or resume |
| `!skip` | Skip current track |
| `!queue` / `!q` | Show queue (paginated) |
| `!clear` | Clear queue and stop |
| `!loop` / `!unloop` | Loop current song |
| `!playlist <url>` | Enqueue playlist (max 50) |
| `!ff` / `!rw` | Seek ±10 seconds |
| `!stop` | Disconnect from voice |

## Project structure

```text
discord-music-bot/
├── main.py           # entrypoint
├── music_cog.py      # playback, queue, YouTube
├── help_cog.py       # help + prefix
├── requirements.txt  # pinned deps
├── run.ps1           # start bot
├── dev.ps1           # auto-restart on .py changes
├── test_inputs.txt   # smoke checklist
├── .env.example
└── .env              # local secrets (gitignored)
```

## Notes

- Secrets stay in `.env` only.
- FFmpeg is required for audio.
- Playback uses a single advance path so skip/seek do not double-fire the next track.
