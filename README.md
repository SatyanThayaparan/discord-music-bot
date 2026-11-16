# Discord Music Bot

Personal Discord bot for playing music in voice channels, with queue controls and YouTube playback.

## Features

- Play songs from YouTube search or links
- Queue management (add, remove, swap, clear)
- Pause, resume, skip, loop
- Playlist import
- Fast-forward / rewind helpers
- Custom help command

## Tech stack

- Python 3
- discord.py
- yt-dlp / YoutubeSearch
- FFmpeg
- Optional: YouTube Data API (thumbnails)

## Setup

1. Clone the repo and enter the project folder:

```bash
git clone https://github.com/SatyanThayaparan/discord-music-bot.git
cd discord-music-bot
```

2. Install [Python 3.10+](https://www.python.org/downloads/) and [FFmpeg](https://ffmpeg.org/download.html). Add `ffmpeg/bin` to your system `PATH`.
3. Create a Discord application and bot at the [Discord Developer Portal](https://discord.com/developers/applications):
   - Enable **Message Content**, **Server Members**, and **Presence** intents
   - Invite the bot with connect, speak, and send-messages permissions
4. Install dependencies:

```bash
pip install discord.py PyNaCl yt_dlp youtubesearchpython pytube python-dotenv google-api-python-client
```

5. Copy the env template and fill in your secrets (`.env` is gitignored):

```bash
copy .env.example .env
```

```env
TOKEN=your_discord_bot_token
YOUTUBE_API_KEY=your_youtube_api_key
```

6. Run the bot:

```bash
python main.py
```

## Usage

Prefix commands with `!` (examples):

| Command | Description |
|---------|-------------|
| `!play <query or url>` | Play or enqueue a track |
| `!pause` / `!resume` | Pause or resume |
| `!skip` | Skip current track |
| `!queue` | Show the queue |
| `!clear` | Clear the queue |
| `!loop` / `!unloop` | Toggle looping |
| `!playlist <url>` | Enqueue a YouTube playlist |
| `!stop` | Disconnect from voice |

## Project structure

```text
discord-music-bot/
├── main.py         # bot entrypoint
├── music_cog.py    # playback and queue commands
├── help_cog.py     # help command
├── .env.example    # template for required secrets
└── .env            # local secrets (gitignored — do not commit)
```

## Notes

- Secrets live only in `.env` on your machine. `.env.example` is safe to commit.
- FFmpeg must be installed for audio playback.
