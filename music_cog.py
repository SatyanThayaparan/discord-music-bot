import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from youtubesearchpython import VideosSearch
import asyncio

class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = False  # Flag to track if music is currently playing
        self.is_paused = False   # Flag to track if music is paused
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
            # If the input is already a URL, extract the title
            title = self.ytdl.extract_info(item, download=False)["title"]
            return {'source': item, 'title': title}
        else:
            # If the input is a search query, search YouTube and return the first result
            search = VideosSearch(item, limit=1)
            return {'source': search.result()["result"][0]["link"], 'title': search.result()["result"][0]["title"]}

    # Function to play the next song in the queue
    async def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True
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
        except:
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
        retval = ""
        for i in range(0, len(self.music_queue)):
            retval += f"#{i+1} -" + self.music_queue[i][0]['title'] + "\n"
        if retval != "":
            await ctx.send(f"queue:\n{retval}")
        else:
            await ctx.send("No music in queue")

    # Command to clear the music queue
    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        if self.vc is not None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        await ctx.send("Music queue cleared")

    # Command to disconnect the bot from the voice channel
    @commands.command(name="stop", aliases=["disconnect", "l", "d"], help="Kick the bot from VC")
    async def dc(self, ctx):
        self.is_playing = False
        self.is_paused = False
        await self.vc.disconnect()

    # Command to remove the last song added to the queue
