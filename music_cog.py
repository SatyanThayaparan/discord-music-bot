import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from youtubesearchpython import VideosSearch
import asyncio
import googleapiclient.discovery

class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = False  # Flag to track if music is currently playing
        self.is_paused = False   # Flag to track if music is paused
        self.is_looping = False  # Flag to track if looping is enabled
        self.current_song = None # Store the current song
        self.music_queue = []    # List to store queued songs
        self.YDL_OPTIONS = {'format': 'bestaudio/best'}  # Options for YoutubeDL
        
        self.FFMPEG_OPTIONS = {                             # FFmpeg options 
            'options': '-vn',  # Disable video processing
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',  # Additional options before input
        }
        self.vc = None           # VoiceClient object for the bot's voice connection
        self.ytdl = YoutubeDL(self.YDL_OPTIONS)           # YoutubeDL object for downloading YouTube videos

    # Function to search YouTube for a song
    def search_yt(self, item):
        if item.startswith("https://"):
            # If the input is already a URL, extract the title and video ID
            info = self.ytdl.extract_info(item, download=False)
            return {'source': item, 'title': info['title'], 'id': info['id']}
        else:
            # If the input is a search query, search YouTube and return the first result
            search = VideosSearch(item, limit=1)
            result = search.result()["result"][0]
            return {'source': result["link"], 'title': result["title"], 'id': result["id"]}

    # Function to get thumbnail URL
    async def get_thumbnail_url(self, video_id):
        api_key = "REDACTED_YOUTUBE_API_KEY"
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
        request = youtube.videos().list(part="snippet", id=video_id)
        response = request.execute()
        thumbnail_url = response['items'][0]['snippet']['thumbnails']['default']['url']
        return thumbnail_url

    # Function to play the next song in the queue
    async def play_next(self):
        if self.is_looping and self.current_song is not None:
            self.music_queue.insert(0, self.current_song)

        if len(self.music_queue) > 0:
            self.is_playing = True
            self.current_song = self.music_queue[0]
            m_url = self.music_queue[0][0]['source']
            self.music_queue.pop(0)
            loop = asyncio.get_event_loop()
            try:
                # Extract info for the next song and play it
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
                song = data['url']
                self.vc.play(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
            except Exception as e:
                # If an error occurs, print the error and attempt to play the next song
                print(f"Error playing next song: {e}")
                self.is_playing = False
                await self.play_next()
        else:
            # If there are no more songs in the queue, set is_playing to False
            self.is_playing = False

    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True
            self.current_song = self.music_queue[0]
            m_url = self.music_queue[0][0]['source']
            if self.vc is None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()
                if self.vc is None:
                    await ctx.send("Could not connect to the voice channel")
                    return
            else:
                await self.vc.move_to(self.music_queue[0][1])
            self.music_queue.pop(0)
            loop = asyncio.get_event_loop()
            try:
                # Extract info for the song and play it
                data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(m_url, download=False))
                song = data['url']
                self.vc.play(discord.FFmpegPCMAudio(song, **self.FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop))
            except Exception as e:
                # If an error occurs, print the error and attempt to play the next song
                print(f"Error playing music: {e}")
                self.is_playing = False
                await self.play_next()
        else:
            # If there are no songs in the queue, set is_playing to False
            self.is_playing = False


    # Command to play a song
    @commands.command(name="play", aliases=["p", "playing"], help="Plays a selected song from YouTube")
    async def play(self, ctx, *args):
        query = " ".join(args)
        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("You need to connect to a voice channel first!")
            return

        if self.is_paused:
            self.vc.resume()
        else:
            song = self.search_yt(query)
            if type(song) == type(True):
                await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
            else:
                self.music_queue.append([song, voice_channel])
                if not self.is_playing:
                    await self.play_music(ctx)

                # Log for debugging
                print(f"Song found: {song}")

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


    # Command to pause the current song
    @commands.command(name="pause", help="Pauses the current song being played")
    async def pause(self, ctx, *args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
        elif self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()

    # Command to resume the paused song
    @commands.command(name="resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx, *args):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()

    # Command to skip the current song
    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        if self.vc is not None and self.vc:
            self.vc.stop()
            await self.play_music(ctx)

    # Command to display the current music queue
    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        if len(self.music_queue) > 0:
            queue_text = "\n".join([f"#{i+1} - {song[0]['title']}" for i, song in enumerate(self.music_queue)])
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
        if self.vc is not None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        embed = discord.Embed(
            description="Music queue cleared",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # Command to disconnect the bot from the voice channel
    @commands.command(name="stop", aliases=["disconnect", "l", "d"], help="Kick the bot from VC")
    async def dc(self, ctx):
        self.is_playing = False
        self.is_paused = False
        await self.vc.disconnect()

    # Command to remove the last song added to the queue
    @commands.command(name="remove", aliases=["rm"], help="Removes the last song added to the queue")
    async def remove(self, ctx):
        if self.music_queue:
            removed_song = self.music_queue.pop()
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

    # Command to add a song at a specific position in the queue
    @commands.command(name="add", aliases=["a"], help="Adds a song to the queue at a specific position")
    async def add_song(self, ctx, position: int, *args):
        query = " ".join(args)
        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.send("You need to connect to a voice channel first!")
            return

        if position < 1 or position > len(self.music_queue) + 1:
            await ctx.send("Invalid position! The position should be between 1 and the current queue length + 1.")
            return

        song = self.search_yt(query)
        if type(song) == type(True):
            await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
        else:
            self.music_queue.insert(position - 1, [song, voice_channel])
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
        if position1 < 1 or position1 > len(self.music_queue) or position2 < 1 or position2 > len(self.music_queue):
            await ctx.send("Invalid positions! The positions should be between 1 and the current queue length.")
            return

        # Swap the positions of the songs
        self.music_queue[position1 - 1], self.music_queue[position2 - 1] = self.music_queue[position2 - 1], self.music_queue[position1 - 1]

        embed = discord.Embed(
            description=f"Swapped positions between songs: **{self.music_queue[position1 - 1][0]['title']}** and **{self.music_queue[position2 - 1][0]['title']}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    # Command to loop the current song
    @commands.command(name="loop", help="Loops the current song")
    async def loop(self, ctx):
        if self.is_playing or self.is_paused:
            self.is_looping = True
            embed = discord.Embed(
                title="Loop Enabled",
                description=f"Looping the current song: **{self.current_song[0]['title']}**",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No song is currently being played.")

    # Command to unloop the current song
    @commands.command(name="unloop", help="Stops looping the current song")
    async def unloop(self, ctx):
        if self.is_looping:
            self.is_looping = False
            embed = discord.Embed(
                title="Loop Disabled",
                description=f"Stopped looping the current song: **{self.current_song[0]['title']}**",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Looping is not enabled.")
