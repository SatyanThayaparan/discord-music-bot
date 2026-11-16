import os
import asyncio

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

from help_cog import help_cog
from music_cog import music_cog

token = os.getenv("TOKEN")
if not token:
    raise ValueError("No TOKEN found in environment variables. Copy .env.example to .env and set TOKEN.")

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
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("------")


async def main():
    async with bot:
        await load_extensions()
        await bot.start(token)


asyncio.run(main())
