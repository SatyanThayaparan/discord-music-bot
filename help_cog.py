import discord
from discord.ext import commands

class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = ""
        self.text_channel_list = []
        self.set_message()

    def set_message(self):
        embed = discord.Embed(
            title="Welcome to the Benji Bot!",
            description="This is an unofficial music bot to play and stream music from YouTube. Below consists of the list of commands and their capabilities.",
            color=discord.Color.blue()  # You can set any color you like
        )

        embed.add_field(
            name="Commands",
            value=(
                f"**{self.bot.command_prefix}help** - Displays all the available commands\n"
                f"**{self.bot.command_prefix}q** - Displays the current music queue\n"
                f"**{self.bot.command_prefix}p <keywords>** - Finds the song on YouTube and plays it in your current channel. Will resume playing the current song if it was paused\n"
                f"**{self.bot.command_prefix}skip** - Skips the current song being played\n"
                f"**{self.bot.command_prefix}clear** - Stops the music and clears the queue\n"
                f"**{self.bot.command_prefix}stop** - Disconnects the bot from the voice channel\n"
                f"**{self.bot.command_prefix}pause** - Pauses the current song being played or resumes if already paused\n"
                f"**{self.bot.command_prefix}resume** - Resumes playing the current song\n"
                f"**{self.bot.command_prefix}prefix <new_prefix>** - Changes the command prefix\n"
                f"**{self.bot.command_prefix}remove** - Removes the last song from the queue"
            ),
            inline=False
        )

        embed.set_footer(text="Enjoy your music! 🎶")

        self.help_message = embed

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Game(f"type {self.bot.command_prefix}help"))

    @commands.command(name="help", help="Displays all the available commands")
    async def help(self, ctx):
        await ctx.send(embed = self.help_message)
    
    @commands.command(name="prefix", help="Change bot prefix")
    async def prefix(self, ctx, new_prefix):
        self.bot.command_prefix = new_prefix
        self.set_message()
        await ctx.send(f"Prefix set to **'{self.bot.command_prefix}'**")
        await self.bot.change_presence(activity=discord.Game(f"type {self.bot.command_prefix}help"))

    @commands.command(name="send_to_all", help="Send a message to all text channels")
    async def send_to_all(self, ctx, *, msg):
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    await channel.send(msg)
                except discord.Forbidden:
                    pass

def setup(bot):
    bot.add_cog(help_cog(bot))