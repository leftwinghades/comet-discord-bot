import discord
from discord.ext import commands
import datetime
import youtube_dl

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []

    YTDL_OPTIONS = {
        "format": "bestaudio/best",
        "noplaylist": "True",
    }

    FFMPEG_OPTIONS = {
        "options": "-vn",
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    }

    LOOP_FLAG = False

    async def search_yt(self, song):
        song_json = await self.bot.loop.run_in_executor(None, lambda: youtube_dl.YoutubeDL(self.YTDL_OPTIONS).extract_info(f"ytsearch:{song}", download=False)["entries"][0])

        song_info = {
            "title": song_json["title"],
            "uploader": song_json["uploader"],
            "duration": song_json["duration"],
            "thumbnail": song_json["thumbnails"][0]["url"],
            "audio_url": song_json["formats"][0]["url"],
            "yt_url": song_json["webpage_url"],
        }
        return song_info


    async def get_song_info(self, yt_url):
        with youtube_dl.YoutubeDL(self.YTDL_OPTIONS) as ydl:

            try:
                song_json = ydl.extract_info(yt_url, download=False)
            except Exception:
                return False

            song_info = {
                "title": song_json["title"],
                "uploader": song_json["uploader"],
                "duration": song_json["duration"],
                "thumbnail": song_json["thumbnails"][0]["url"],
                "audio_url": song_json["formats"][0]["url"],
                "yt_url": song_json["webpage_url"],
            }
            return song_info

    async def clean_up(self, ctx):
        self.song_queue.clear()
        self.LOOP_FLAG= False
        await ctx.voice_client.disconnect()

    async def get_total_duration(self, pos_in_queue=None):
        total_duration = 0
        for song in self.song_queue[:pos_in_queue]:
            total_duration += song["duration"]
        return total_duration
            
    async def check_queue(self, ctx):
        if len(ctx.voice_client.channel.members) < 2:
            dc_message = f"There are no users in {ctx.voice_client.channel.name}. Comet has now disconnected from {ctx.voice_client.channel.name}"
            await self.clean_up(ctx)
            return await ctx.send(dc_message)
        elif self.LOOP_FLAG == True:
            await self.play_song(ctx, self.song_queue[0]["audio_url"])
        elif len(self.song_queue) <= 1:
            dc_message = f"The song queue has now finished. Comet has now disconnected from {ctx.voice_client.channel.name}"
            await self.clean_up(ctx)
            return await ctx.send(dc_message)
        else:
            await self.play_song(ctx, self.song_queue[1]["audio_url"])
            self.song_queue.pop(0)

    async def play_song(self, ctx, audio_url):
        ctx.voice_client.play(discord.FFmpegPCMAudio(audio_url, **self.FFMPEG_OPTIONS), after=lambda error: self.bot.loop.create_task(self.check_queue(ctx)))

    @commands.command(aliases=["p"], brief='p', description='This is the full description')
    async def play(self, ctx, *, song=None):
        if ctx.author.voice is None: # if user is not in vc
            return await ctx.send("You need to be in voice channel to use this command")
        elif ctx.author.voice is not None and ctx.voice_client is not None and ctx.author.voice.channel.name != ctx.voice_client.channel.name: # if user is in vc and bot is in a different vc
            return await ctx.send("You need to be in the same voice channel as Comet to use this command")
        elif ctx.author.voice is not None and ctx.voice_client is None: # user is in vc and bot is not in vc
            await ctx.author.voice.channel.connect()
            await ctx.send(f"Comet has now joined {ctx.author.voice.channel.name}")

        if song is None:
            return await ctx.send("Parameters not given")

        if "youtube.com/watch?" in song or "https://youtu.be/" in song:
            song_info = await self.get_song_info(song)

            if song_info == False:
                return await ctx.send("The requested song is unavailble")

        # handle song where song isn't a youtube url
        else:
            await ctx.send(f"Searching for \"{song}\"")
            song_info = await self.search_yt(song)

            if song_info is None:
                return await ctx.send("Song could not be found. Try using the Youtube URL")

        if len(self.song_queue) > 0:
            self.song_queue.append(song_info)

            song_eta = await self.get_total_duration(-1)
            embed = discord.Embed(title="Added to queue", description="", color=discord.Color.gold())
            embed.description += f"[{self.song_queue[len(self.song_queue)-1]['title']}]({self.song_queue[len(self.song_queue)-1]['yt_url']})\n"
            embed.set_thumbnail(url=song_info["thumbnail"])
            embed.add_field(name="Channel", value=song_info["uploader"], inline=True)
            embed.add_field(name="Song Duration", value=str(datetime.timedelta(seconds=song_info["duration"])), inline=True)
            embed.add_field(name="Estimated time until playing", value=str(datetime.timedelta(seconds=song_eta)), inline=True)
            embed.add_field(name="Position in queue", value=len(self.song_queue)-1, inline=True)
            return await ctx.send(embed=embed)

        self.song_queue.append(song_info)
        await self.play_song(ctx, song_info["audio_url"])
        await ctx.send(f"Now playing: {song_info['title']}")

    @commands.command(aliases=["summon"], brief='summon', description='This is the full description')
    async def join(self, ctx):
        if ctx.author.voice is None: # if user is not in vc
            return await ctx.send("You need to be in voice channel to use this command")
        elif ctx.author.voice is not None and ctx.voice_client is None: # user is in vc and bot is not in vc
            await ctx.author.voice.channel.connect()
            return await ctx.send(f"Comet has now joined {ctx.author.voice.channel.name}")
        elif ctx.author.voice is not None and ctx.voice_client is not None: # if user is in vc and bot is in vc
            if ctx.author.voice.channel.name == ctx.voice_client.channel.name: # if user is in vc and bot is in the same vc 
                return await ctx.send(f"Comet had already joined {ctx.author.voice.channel.name}")
            else: # if user and bot are in different vc
                await ctx.voice_client.disconnect()
                await ctx.author.voice.channel.connect()
                return await ctx.send(f"Comet has now joined {ctx.author.voice.channel.name}")

    @commands.command(aliases=["dc"], brief='dc', description='This is the full description')
    async def disconnect(self, ctx):
        if ctx.author.voice is None: # if user is not in vc
            return await ctx.send("You need to be in voice channel to use this command")
        elif ctx.author.voice is not None and ctx.voice_client is not None: # if user is in vc and bot is in vc
            if ctx.author.voice.channel.name == ctx.voice_client.channel.name: # if user is in vc and bot is in the same vc 
                dc_message = f"Comet has now disconnected from {ctx.voice_client.channel.name}"
                await self.clean_up(ctx)
                return await ctx.send(dc_message)
            else: # if user and bot are in different vc
                return await ctx.send("You need to be in the same voice channel as Comet to use this command")
        else:
            return await ctx.send("Comet has not joined a voice channel")

    @commands.command(aliases=["q"], brief='q', description='This is the full description')
    async def queue(self, ctx):
        if len(self.song_queue) == 0:
            return await ctx.send("The song queue is empty")
        embed = discord.Embed(title="Song Queue", description="", colour=discord.Colour.dark_gold())
        embed.description += f"__Now Playing:__\n[{self.song_queue[0]['title']}]({self.song_queue[0]['yt_url']}) | {str(datetime.timedelta(seconds=self.song_queue[0]['duration']))}\n\n"
        embed.description += f"__Up Next:__\n"
        i = 1
        total_duration = await self.get_total_duration()
        for song in self.song_queue[1:]:
            embed.description += f"{i}. [{song['title']}]({song['yt_url']}) | {str(datetime.timedelta(seconds=song['duration']))}\n"
            i += 1
        embed.description += f"\n**{i-1} songs in queue | {str(datetime.timedelta(seconds=total_duration))} total duration**"
        await ctx.send(embed=embed)

    @commands.command(aliases=["np"], brief='np', description='This is the full description')
    async def nowplaying(self, ctx):
        if len(self.song_queue) == 0:
            return await ctx.send("There is no song currently playing")
        embed = discord.Embed(title="Now Playing", description="", colour=discord.Colour.dark_green())
        embed.description += f"[{self.song_queue[0]['title']}]({self.song_queue[0]['yt_url']})"
        embed.set_thumbnail(url=self.song_queue[0]["thumbnail"])
        embed.add_field(name="Channel", value=self.song_queue[0]["uploader"], inline=True)
        embed.add_field(name="Song Duration", value=str(datetime.timedelta(seconds=self.song_queue[0]["duration"])), inline=True)
        await ctx.send(embed=embed)

    @commands.command(aliases=["fs"], brief='fs', description='This is the full description')
    async def skip(self, ctx):
        if ctx.author.voice is None: # if user is not in vc
            return await ctx.send("You need to be in voice channel to use this command")
        elif ctx.author.voice is not None and ctx.voice_client is not None: # if user is in vc and bot is in vc
            if ctx.author.voice.channel.name == ctx.voice_client.channel.name: # if user is in vc and bot is in the same vc 
                if ctx.voice_client.is_playing():
                    ctx.voice_client.stop()
                    return await ctx.send(f"{self.song_queue[0]['title']} has been skipped by {ctx.author}")
                else:
                    return await ctx.send("There is no song currently playing")
            else: # if user and bot are in different vc
                return await ctx.send("You need to be in the same voice channel as Comet to use this command")
        else:
            return await ctx.send("Comet has not joined a voice channel")

    @commands.command(aliases=["cl"], brief='cl', description='This is the full description')
    async def clear(self, ctx):
        if ctx.author.voice is None: # if user is not in vc
            return await ctx.send("You need to be in voice channel to use this command")
        elif ctx.author.voice is not None and ctx.voice_client is not None: # if user is in vc and bot is in vc
            if ctx.author.voice.channel.name == ctx.voice_client.channel.name: # if user is in vc and bot is in the same vc 
                self.song_queue.clear()
                return await ctx.send("The song queue has been cleared")
            else: # if user and bot are in different vc
                return await ctx.send("You need to be in the same voice channel as Comet to use this command")
        else:
            return await ctx.send("Comet has not joined a voice channel")

    @commands.command(aliases=["lp"], brief='lp', description='This is the full description')
    async def loop(self, ctx):
        if ctx.author.voice is None: # if user is not in vc
            return await ctx.send("You need to be in voice channel to use this command")
        elif ctx.author.voice is not None and ctx.voice_client is not None: # if user is in vc and bot is in vc
            if ctx.author.voice.channel.name == ctx.voice_client.channel.name: # if user is in vc and bot is in the same vc 
                if ctx.voice_client.is_playing():
                    if self.LOOP_FLAG == False:
                        self.LOOP_FLAG = True
                        return await ctx.send(f"Loop enabled")
                    else:
                        self.LOOP_FLAG = False
                        return await ctx.send(f"Loop disabled")
                else:
                    return await ctx.send("There is no song currently playing")
            else: # if user and bot are in different vc
                return await ctx.send("You need to be in the same voice channel as Comet to use this command")
        else:
            return await ctx.send("Comet has not joined a voice channel")

    @commands.command(aliases=["rm"], brief='rm', description='This is the full description')
    async def remove(self, ctx, queue_pos=None):
        if ctx.author.voice is None: # if user is not in vc
            return await ctx.send("You need to be in voice channel to use this command")
        elif ctx.author.voice is not None and ctx.voice_client is not None and ctx.author.voice.channel.name != ctx.voice_client.channel.name: # if user is in vc and bot is in a different vc
            return await ctx.send("You need to be in the same voice channel as Comet to use this command")
        elif ctx.voice_client is None: # user is in vc and bot is not in vc
            return await ctx.send("Comet has not joined a voice channel")

        try:
            queue_pos = int(queue_pos)

            if queue_pos > 0 and queue_pos <= len(self.song_queue):
                    removed_song = f"{self.song_queue[queue_pos]['title']} has been removed from the queue by {ctx.author}"
                    self.song_queue.pop(queue_pos)
                    return await ctx.send(removed_song)
            else:
                return await ctx.send("Parameter not given or is invalid")
        except ValueError:
            return await ctx.send("Parameter not given or is invalid")
        except TypeError:
            return await ctx.send("Parameter not given or is invalid")