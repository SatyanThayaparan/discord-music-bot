import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

from help_cog import help_cog
from music_cog import music_cog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("shiori-bot")

token = os.getenv("TOKEN")
if not token:
    raise ValueError(
        "No TOKEN found in environment variables. Copy .env.example to .env and set TOKEN."
    )

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")


async def load_extensions():
    await bot.add_cog(help_cog(bot))
    await bot.add_cog(music_cog(bot))


@bot.event
async def on_ready():
    log.info("Logged in as %s (%s)", bot.user.name, bot.user.id)


async def main():
    async with bot:
        await load_extensions()
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
