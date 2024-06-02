import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Import all of the cogs
from help_cog import help_cog
from music_cog import music_cog

# Load environment variables from .env file
load_dotenv()

# Debugging: Print the loaded TOKEN value
token = os.getenv('TOKEN')
print(f"TOKEN: {token}")  # Debug print
if token is None:
    raise ValueError("No TOKEN found in environment variables")

# Request the necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.presences = True  # Enable Presence Intent
intents.members = True  # Enable Server Members Intent

bot = commands.Bot(command_prefix='!', intents=intents)

# Remove the default help command so that we can write our own
bot.remove_command('help')

async def load_extensions():
    await bot.add_cog(help_cog(bot))
    await bot.add_cog(music_cog(bot))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')

async def main():
    async with bot:
        await load_extensions()
        await bot.start(token)  # Use the token variable

asyncio.run(main())
