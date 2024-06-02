import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debugging: Print the loaded TOKEN value
token = os.getenv('TOKEN')
print(f"TOKEN: {token}")  # Debug print
if token is None:
    raise ValueError("No TOKEN found in environment variables")

# Import all of the cogs
from help_cog import help_cog
from music_cog import music_cog

# Request the necessary intents
intents = discord.Intents.default()
intents.presences = True  # Enable Presence Intent
intents.members = True  # Enable Server Members Intent

bot = commands.Bot(command_prefix='+', intents=intents)

# Remove the default help command so that we can write our own
bot.remove_command('help')

async def main():
    async with bot:
        await bot.add_cog(help_cog(bot))
        await bot.add_cog(music_cog(bot))
        await bot.start(token)  # Use the token variable

asyncio.run(main())
