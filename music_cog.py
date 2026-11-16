import os
import asyncio

import discord
import googleapiclient.discovery
from discord.ext import commands
from dotenv import load_dotenv
from pytube import Playlist
from yt_dlp import YoutubeDL
from youtubesearchpython import VideosSearch

load_dotenv()


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_settings = {}  # Dictionary to store settings for each guild

    def ensure_guild_settings(self, guild_id):
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = {
                'is_playing': False,
                'is_paused': False,
                'is_looping': False,
                'current_song': None,
                'music_queue': [],
                'vc': None,
                'seek_position': 0
            }

    # Function to search YouTube for a song
    def search(self, item):
        ytdl_options = {'format': 'bestaudio/best'}
        ytdl = YoutubeDL(ytdl_options)
        if item.startswith("https://"):
            info = ytdl.extract_info(item, download=False)
            return {'source': item, 'title': info['title'], 'id': info['id']}
        else:
            search = VideosSearch(item, limit=1)
            result = search.result()["result"][0]
            return {'source': result["link"], 'title': result["title"], 'id': result["id"]}

    # Function to get thumbnail URL
    async def get_thumbnail_url(self, video_id):
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return None
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
        request = youtube.videos().list(part="snippet", id=video_id)
        response = request.execute()
        thumbnail_url = response['items'][0]['snippet']['thumbnails']['default']['url']
        return thumbnail_url

    # Function to play the next song in the queue
    async def play_next(self, guild_id):
        settings = self.guild_settings[guild_id]
        if settings['is_looping'] and settings['current_song'] is not None:
            settings['music_queue'].insert(0, settings['current_song'])

        if len(settings['music_queue']) > 0:
            settings['is_playing'] = True
            settings['current_song'] = settings['music_queue'][0]
            m_url = settings['music_queue'][0][0]['source']
            settings['music_queue'].pop(0)
            loop = asyncio.get_event_loop()
            try:
                ytdl_options = {'format': 'bestaudio/best'}
                ytdl = YoutubeDL(ytdl_options)
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(m_url, download=False))
                song = data['url']
                settings['vc'].play(discord.FFmpegPCMAudio(song, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn'), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop))
            except Exception as e:
                print(f"Error playing next song: {e}")
                settings['is_playing'] = False
                await self.play_next(guild_id)
        else:
            settings['is_playing'] = False

    async def play_music(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if len(settings['music_queue']) > 0:
            settings['is_playing'] = True
            settings['current_song'] = settings['music_queue'][0]
            m_url = settings['music_queue'][0][0]['source']
            if settings['vc'] is None or not settings['vc'].is_connected():
                settings['vc'] = await settings['music_queue'][0][1].connect()
                if settings['vc'] is None:
                    await ctx.send("Could not connect to the voice channel")
                    return
            else:
                await settings['vc'].move_to(settings['music_queue'][0][1])
            settings['music_queue'].pop(0)
            settings['seek_position'] = 0
            loop = asyncio.get_event_loop()
            try:
                ytdl_options = {'format': 'bestaudio/best'}
                ytdl = YoutubeDL(ytdl_options)
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(m_url, download=False))
                song = data['url']
                settings['vc'].play(discord.FFmpegPCMAudio(song, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn'), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop))
            except Exception as e:
                print(f"Error playing music: {e}")
                settings['is_playing'] = False
                await self.play_next(guild_id)
        else:
            settings['is_playing'] = False

    async def seek(self, ctx, seconds: int):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if settings['current_song'] is None:
            await ctx.send("No song is currently playing.")
            return

        settings['seek_position'] += seconds
        if settings['seek_position'] < 0:
            settings['seek_position'] = 0

        m_url = settings['current_song'][0]['source']
        loop = asyncio.get_event_loop()
        try:
            ytdl_options = {'format': 'bestaudio/best'}
            ytdl = YoutubeDL(ytdl_options)
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(m_url, download=False))
            song = data['url']
            ffmpeg_options = '-vn -ss {seek_position}'.format(seek_position=settings['seek_position'])
            settings['vc'].stop()
            settings['vc'].play(discord.FFmpegPCMAudio(song, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options=ffmpeg_options), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(guild_id), self.bot.loop))
        except Exception as e:
            print(f"Error seeking in the song: {e}")
            await ctx.send("An error occurred while trying to seek in the song.")

    @commands.command(name="play", aliases=["p", "playing"], help="Plays a selected song from YouTube or Spotify")
    async def play(self, ctx, *args):
        query = " ".join(args)
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("You need to connect to a voice channel first!")
            return

        if settings['is_paused']:
            settings['vc'].resume()
        else:
            song = self.search(query)
            if not song:
                await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
            else:
                settings['music_queue'].append([song, voice_channel])
                if not settings['is_playing']:
                    await self.play_music(ctx)

                print(f"Song found: {song}")

                try:
                    thumbnail_url = await self.get_thumbnail_url(song['id'])
                except Exception as e:
                    print(f"Error getting thumbnail: {e}")
                    thumbnail_url = None

                embed = discord.Embed(
                    title=f"Added to the Queue: {song['title']}",
                    description=f"[Watch on YouTube]({song['source']})",
                    color=discord.Color.green()
                )
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                embed.set_footer(text="Enjoy your music! 🎶")

                await ctx.send(embed=embed)

    @commands.command(name="ff", help="Fast forwards the current song by 10 seconds")
    async def fast_forward(self, ctx):
        await self.seek(ctx, 10)

    @commands.command(name="rw", help="Rewinds the current song by 10 seconds")
    async def rewind(self, ctx):
        await self.seek(ctx, -10)

    @commands.command(name="playlist", help="Adds all songs from a YouTube playlist to the queue")
    async def add_playlist_to_queue(self, ctx, playlist_url):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        try:
            playlist = Playlist(playlist_url)
            if not playlist.videos:
                await ctx.send(embed=discord.Embed(
                    title="Playlist Error",
                    description="No valid videos found in the playlist.",
                    color=discord.Color.red()
                ))
                return

            for video in playlist.videos:
                if video.video_id:
                    song = self.search(video.watch_url)
                    if song:
                        settings['music_queue'].append([song, ctx.author.voice.channel])

            await ctx.send(embed=discord.Embed(
                title="Playlist Added",
                description=f"All songs from the playlist have been added to the queue.",
                color=discord.Color.green()
            ))

            if not settings['is_playing']:
                await self.play_music(ctx)
        except Exception as e:
            print(f"Error adding playlist: {e}")
            await ctx.send(embed=discord.Embed(
                title="Playlist Error",
                description="An error occurred while adding the playlist.",
                color=discord.Color.red()
            ))

    # Command to pause the current song
    @commands.command(name="pause", help="Pauses the current song being played")
    async def pause(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if settings['is_playing']:
            settings['is_playing'] = False
            settings['is_paused'] = True
            settings['vc'].pause()
        elif settings['is_paused']:
            settings['is_paused'] = False
            settings['is_playing'] = True
            settings['vc'].resume()

    # Command to resume the paused song
    @commands.command(name="resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if settings['is_paused']:
            settings['is_paused'] = False
            settings['is_playing'] = True
            settings['vc'].resume()

    # Command to skip the current song
    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if settings['vc'] is not None and settings['vc']:
            settings['vc'].stop()
            await self.play_music(ctx)

    # Command to display the current music queue
    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if len(settings['music_queue']) > 0:
            queue_text = "\n".join([f"#{i+1} - {song[0]['title']}" for i, song in enumerate(settings['music_queue'])])
            embed = discord.Embed(
                title="Current Queue",
                description=queue_text,
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description="No music in queue",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    # Command to clear the music queue
    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if settings['vc'] is not None and settings['is_playing']:
            settings['vc'].stop()
        settings['music_queue'] = []
        embed = discord.Embed(
            description="Music queue cleared",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # Command to disconnect the bot from the voice channel
    @commands.command(name="stop", aliases=["disconnect", "l", "d"], help="Kick the bot from VC")
    async def dc(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        settings['is_playing'] = False
        settings['is_paused'] = False
        await settings['vc'].disconnect()

    # Command to remove the last song added to the queue
    @commands.command(name="remove", aliases=["rm"], help="Removes the last song added to the queue")
    async def remove(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if settings['music_queue']:
            removed_song = settings['music_queue'].pop()
            embed = discord.Embed(
                description=f"Removed {removed_song[0]['title']} from the queue.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description="The queue is empty.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    # Command to remove a song at a specified position
    @commands.command(name="removeat", aliases=["rmat"], help="Removes a song at the specified position in the queue")
    async def remove_at(self, ctx, position: int):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if 0 < position <= len(settings['music_queue']):
            removed_song = settings['music_queue'].pop(position - 1)
            embed = discord.Embed(
                description=f"Removed {removed_song[0]['title']} from position {position} in the queue.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"Invalid position. The queue currently has {len(settings['music_queue'])} songs.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    # Command to remove multiple songs
    @commands.command(name="removemultiple", aliases=["rmulti", "rmm"], help="Removes songs from the queue")
    async def remove_multiple(self, ctx, *positions: int):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if len(positions) == 0:
            await ctx.send("Please specify the positions of the songs you want to remove.")
            return

        removed_songs = []
        for position in sorted(set(positions), reverse=True):
            if 0 < position <= len(settings['music_queue']):
                removed_songs.append(settings['music_queue'].pop(position - 1)[0]['title'])

        if removed_songs:
            embed = discord.Embed(
                description=f"Removed the following songs from the queue:\n{', '.join(removed_songs)}",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No songs were removed. Make sure you specify valid positions.")

    # Command to add a song at a specific position in the queue
    @commands.command(name="add", aliases=["a"], help="Adds a song to the queue at a specific position")
    async def add_song(self, ctx, position: int, *args):
        query = " ".join(args)
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("You need to connect to a voice channel first!")
            return

        if position < 1 or position > len(settings['music_queue']) + 1:
            await ctx.send("Invalid position! The position should be between 1 and the current queue length + 1.")
            return

        song = self.search(query)
        if type(song) == type(True):
            await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
        else:
            settings['music_queue'].insert(position - 1, [song, voice_channel])
            # Log for debugging
            print(f"Song added at position {position}: {song}")

            try:
                thumbnail_url = await self.get_thumbnail_url(song['id'])
            except Exception as e:
                print(f"Error getting thumbnail: {e}")
                thumbnail_url = None

            # Create an embed message with the song's title and a thumbnail
            embed = discord.Embed(
                title=f"Added to the Queue: {song['title']}",
                description=f"[Watch on YouTube]({song['source']})",
                color=discord.Color.green()
            )
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            embed.set_footer(text="Enjoy your music! 🎶")

            await ctx.send(embed=embed)

    # Command to swap the positions of songs in the queue
    @commands.command(name="swap", help="Swaps the positions of songs in the queue")
    async def swap_songs(self, ctx, position1: int, position2: int):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if position1 < 1 or position1 > len(settings['music_queue']) or position2 < 1 or position2 > len(settings['music_queue']):
            await ctx.send("Invalid positions! The positions should be between 1 and the current queue length.")
            return

        # Swap the positions of the songs
        settings['music_queue'][position1 - 1], settings['music_queue'][position2 - 1] = settings['music_queue'][position2 - 1], settings['music_queue'][position1 - 1]

        embed = discord.Embed(
            description=f"Swapped positions between songs: **{settings['music_queue'][position1 - 1][0]['title']}** and **{settings['music_queue'][position2 - 1][0]['title']}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    # Command to loop the current song
    @commands.command(name="loop", help="Loops the current song")
    async def loop(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if settings['is_playing'] or settings['is_paused']:
            settings['is_looping'] = True
            embed = discord.Embed(
                title="Loop Enabled",
                description=f"Looping the current song: **{settings['current_song'][0]['title']}**",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No song is currently being played.")

    # Command to unloop the current song
    @commands.command(name="unloop", help="Stops looping the current song")
    async def unloop(self, ctx):
        guild_id = ctx.guild.id
        self.ensure_guild_settings(guild_id)
        settings = self.guild_settings[guild_id]

        if settings['is_looping']:
            settings['is_looping'] = False
            embed = discord.Embed(
                title="Loop Disabled",
                description=f"Stopped looping the current song: **{settings['current_song'][0]['title']}**",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Looping is not enabled.")
