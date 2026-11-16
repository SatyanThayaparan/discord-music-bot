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
- Optional: YouTube Data API (thumbnails), Spotify-related packages if enabled in your environment

## Setup

1. Install [Python 3.10+](https://www.python.org/downloads/) and [FFmpeg](https://ffmpeg.org/download.html). Add `ffmpeg/bin` to your system `PATH`.
2. Create a Discord application and bot at the [Discord Developer Portal](https://discord.com/developers/applications). Enable **Message Content**, **Server Members**, and **Presence** intents. Invite the bot with connect/speak/send-messages permissions.
3. Install dependencies:

```bash
pip install discord.py PyNaCl yt_dlp youtubesearchpython pytube python-dotenv google-api-python-client
```

4. Create a `.env` file in the project root (never commit this file):

```env
TOKEN=your_discord_bot_token
YOUTUBE_API_KEY=your_youtube_api_key_optional
```

5. Run the bot:

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
└── .env            # local secrets (not committed)
```

## Notes

- Store the Discord token and any API keys in `.env` only. Rotate any keys that were previously shared in chat or older README copies.
- FFmpeg must be installed for audio playback.
