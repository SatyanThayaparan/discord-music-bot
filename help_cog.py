import logging

import discord
from discord.ext import commands

from brand import BRAND_NAME, BRAND_TAGLINE, EMBED_PRIMARY, FOOTER_DEFAULT, accent_embed

log = logging.getLogger(__name__)


class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def build_help_embeds(self) -> list[discord.Embed]:
        p = self.bot.command_prefix
        name = self.bot.user.display_name if self.bot.user else BRAND_NAME

        hero = discord.Embed(
            title=name,
            description=(
                f"{BRAND_TAGLINE}\n"
                f"Join a VC, then `{p}play`. Use the buttons on the Now Playing panel for controls."
            ),
            color=EMBED_PRIMARY,
        )
        if self.bot.user:
            hero.set_thumbnail(url=self.bot.user.display_avatar.url)
            hero.set_author(
                name="Command guide",
                icon_url=self.bot.user.display_avatar.url,
            )
        else:
            hero.set_author(name="Command guide")

        hero.add_field(
            name="Playback",
            value=(
                f"`{p}play` / `{p}p` `<query|url>` — search picker or play URL\n"
                f"`{p}pause` — pause (or resume if paused)\n"
                f"`{p}resume` / `{p}r` — resume\n"
                f"`{p}skip` / `{p}s` — next track\n"
                f"`{p}ff` / `{p}rw` — seek ±10 seconds\n"
                f"`{p}volume` / `{p}vol` `[0-200]` — show or set volume\n"
                f"`{p}loop` / `{p}unloop` — repeat current song\n"
                f"`{p}stop` — leave voice"
            ),
            inline=False,
        )
        hero.add_field(
            name="Queue & playlists",
            value=(
                f"`{p}queue` / `{p}q` — show what's up next\n"
                f"`{p}playlist` `<url>` — add up to 50 YouTube tracks\n"
                f"`{p}save` `<name>` — save now+queue as a playlist\n"
                f"`{p}load` `<name>` — load a saved playlist\n"
                f"`{p}playlists` — list saved playlists\n"
                f"`{p}delplaylist` `<name>` — delete a saved playlist\n"
                f"`{p}clear` — wipe the queue\n"
                f"`{p}remove` / `{p}rm` — drop the last queued song\n"
                f"`{p}removeat` / `{p}rmat` `<n>` — drop position *n*\n"
                f"`{p}add` / `{p}a` `<n> <query>` — insert at position\n"
                f"`{p}swap` `<a> <b>` — swap two positions"
            ),
            inline=False,
        )
        hero.add_field(
            name="Bot",
            value=(
                f"`{p}help` — this menu\n"
                f"`{p}prefix` `<new>` — change prefix until restart\n"
                "Leaves VC after 5 minutes alone or fully idle."
            ),
            inline=False,
        )
        hero.set_footer(text=f"{FOOTER_DEFAULT}  ·  prefix {p}")

        return [hero]

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{self.bot.command_prefix}help",
            )
        )

    @commands.command(name="help", help="Displays all the available commands")
    async def help(self, ctx):
        embeds = self.build_help_embeds()
        await ctx.send(embed=embeds[0])

    @commands.command(name="prefix", help="Change bot prefix")
    async def prefix(self, ctx, new_prefix: str):
        self.bot.command_prefix = new_prefix
        await ctx.send(
            embed=accent_embed(
                f"Prefix set to **`{self.bot.command_prefix}`** (until restart)"
            )
        )
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{self.bot.command_prefix}help",
            )
        )
