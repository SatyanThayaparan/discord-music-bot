import discord
from discord.ext import commands

class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = ""
        self.text_channel_list = []
        self.set_message()

    def set_message(self):

        print("Setting help message...") #DEBUG
        # List of commands
        commands_list = [
            f"**{self.bot.command_prefix}help** - Displays all the available commands",
            f"**{self.bot.command_prefix}q** - Displays the current music queue",
            f"**{self.bot.command_prefix}p <keywords>** - Finds the song on YouTube and plays it in your current channel",
            f"**{self.bot.command_prefix}playlist <playlist url>** - Plays and queues all songs from YouTube playlist",
            f"**{self.bot.command_prefix}skip** - Skips the current song being played",
            f"**{self.bot.command_prefix}clear** - Stops the music and clears the queue",
            f"**{self.bot.command_prefix}stop** - Disconnects the bot from the voice channel",
            f"**{self.bot.command_prefix}pause** - Pauses the current song being played or resumes if already paused",
            f"**{self.bot.command_prefix}resume** - Resumes playing the current song",
            f"**{self.bot.command_prefix}prefix <new_prefix>** - Changes the command prefix",
            f"**{self.bot.command_prefix}remove** - Removes the last song from the queue",
            f"**{self.bot.command_prefix}removeat <position>** - Removes a song at the specified position in the queue",
            f"**{self.bot.command_prefix}removemultiple <positions>** - Removes songs from the queue at the specified positions",
            f"**{self.bot.command_prefix}loop** - Loops the current song",
            f"**{self.bot.command_prefix}unloop** - Stops looping the current song",
            f"**{self.bot.command_prefix}add <position> <keywords>** - Adds a song to the queue at a specific position",
            f"**{self.bot.command_prefix}swap <position1> <position2>** - Swaps the positions of songs in the queue",
            f"**{self.bot.command_prefix}ff** - Fast forwards the current song by 5 seconds",
            f"**{self.bot.command_prefix}rw** - Rewinds the current song by 5 seconds"
            # Add more commands here
        ]

        # Split commands into chunks to fit into embed fields
        chunk_size = 12  # Number of commands per embed
        chunks = [commands_list[i:i+chunk_size] for i in range(0, len(commands_list), chunk_size)]

        # Create embeds for each chunk
        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title="Welcome to the Benji Bot!" if i == 0 else None,
                description="This is an unofficial music bot to play and stream music from YouTube. Below consists of the list of commands and their capabilities." if i == 0 else None,
                color=discord.Color.blue()
            )

            # Add commands to embed
            value = "\n".join(chunk)
            embed.add_field(name="Commands" if i == 0 else "", value=value, inline=False)  # Use "\u200b" to add a blank field
            if i == len(chunks) - 1:  # Check if it's the last chunk
                embed.set_footer(text="Enjoy your music! 🎶")

            # Append embed to list
            embeds.append(embed)



        self.help_messages = embeds
        
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(activity=discord.Game(f"type {self.bot.command_prefix}help"))

    @commands.command(name="help", help="Displays all the available commands")
    async def help(self, ctx):
        if not self.help_messages:
            await ctx.send("Help message is not set.")
            return

        for embed in self.help_messages:
            await ctx.send(embed=embed)

    
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