import asyncio
from io import StringIO
import random
import discord
from discord.ext import commands
import aiohttp
from typing import Literal, Optional
import re
import yt_dlp
import sys
import traceback
from discord import app_commands
from utils.classes import BotError
from utils.constants import GUILDS_DB as DB
from utils.functions import from_seconds_to_time_format, from_time_format_to_seconds, get_default_embed
from views import Confirm, Pagelist
from .constants import *
from .functions import *
from .views import *
from .classes import *


class Queue(object):
    def __init__(self):
        self._queue: list[Track] = []
        self._history: list[Track] = []
        self.repeat_mode = RepeatMode.NONE

    @property
    def is_empty(self):
        return not self._queue

    @property
    def current_track(self):
        if not self._queue:
            raise BotError('Queue is empty.', 43, 'music')
        return self._queue[0]

    @property
    def upcoming(self):
        if not self._queue:
            raise BotError('Queue is empty.', 43, 'music')
        return self._queue[1:]

    @property
    def history(self):
        return self._history

    @property
    def queue(self):
        return self._queue

    @property
    def length(self):
        return len(self._queue)

    def add(self, *args):
        self._queue.extend(args)

    def addleft(self, *args):
        self._queue = list(args) + self._queue

    def get_next_track(self):
        if not self._queue:
            raise BotError('Queue is empty.', 43, 'music')
        if self.repeat_mode == RepeatMode.ONE:
            pass
        elif self.repeat_mode == RepeatMode.ALL:
            self._queue.append(self._queue.pop(0))
        else:
            self._history.append(self._queue.pop(0))
            if len(self._history) > 15:
                self._history.pop(0)

        return self._queue[0] if self._queue else None

    def get_to_track(self, place):
        if not self._queue:
            raise BotError('Queue is empty.', 43, 'music')
        queuebefore = self.queue
        historybefore = self.history
        place -= 1
        place = min(len(self._queue)-2, place)
        for i in range(place):
            if self.repeat_mode == RepeatMode.ALL:
                self._queue.append(self._queue.pop(0))
            else:
                self._history.append(self._queue.pop(0))
                if len(self._history) > 15:
                    self._history.pop(0)
        try:
            track = self._queue[1]
        except IndexError:
            self._queue = queuebefore
            self._history = historybefore
            raise BotError('The <place> parameter is invalid.', 43, 'music')
        else:
            return track

    def get_multiple_previous_tracks(self, positions):
        length = len(self._history)
        if length <= 0:
            raise BotError("No tracks found.", 44, 'music')
        positions = reversed(sorted(set(positions)))
        tracks: list[Track] = []
        for position in positions:
            if position < 1:
                break
            if position > length:
                continue
            position -= 1
            tracks.append(self._history.pop(position))
        tf = True if self._queue else False
        if tf:
            self.addleft(*tracks)
        else:
            self._queue = tracks
        return tracks, tf

    def remove_multiple_tracks(self, positions):
        if self.is_empty:
            raise BotError('Queue is empty.', 43, 'music')
        positions = reversed(sorted(set(positions)))
        length = self.length
        tracks: list[Track] = []
        for position in positions:
            if position < 0:
                break
            if position > length - 1:
                continue
            tracks.append(self.queue.pop(position))
        return tracks

    def shuffle(self):
        if not self._queue:
            raise BotError('Queue is empty.', 43, 'music')
        if len(self._queue) < 2:
            return
        upcoming = self.upcoming
        random.shuffle(upcoming)
        self._queue = self._queue[:1]
        self._queue.extend(upcoming)

    def set_repeat_mode(self, mode):
        if mode == "none":
            self.repeat_mode = RepeatMode.NONE
        elif mode == "1" or mode == "one":
            self.repeat_mode = RepeatMode.ONE
        else:
            self.repeat_mode = RepeatMode.ALL

    def empty_history(self):
        self._history.clear()

    def empty(self):
        self._queue.clear()


class MusicPlayer(object):
    def __init__(self, ctx: commands.Context, music):
        self.ctx = ctx
        self.music: MusicContainer = music
        self.bot = ctx.bot
        self.prefix: str = self.bot.cmd_pre
        self.loop = self.bot.loop
        self.queue = Queue()
        self.settings = PlayerSettings()
        self.schedule_member: list[discord.Member] = []
        self.on_count = False
        self.volume = 1.0

    @property
    def current_queue(self):
        if not self.queue._queue:
            raise BotError('Queue is empty.', 43, 'music')
        return self.queue._queue

    @property
    def is_playing(self):
        return self.ctx.voice_client.is_playing()

    @property
    def is_paused(self):
        return self.ctx.voice_client.is_paused()

    @property
    def is_connected(self):
        return self.ctx.voice_client.is_connected()

    async def connect(self, ctx: commands.Context):
        voice = ctx.author.voice
        if not voice:
            raise BotError('No voice channel.', 42, 'music')
        if (channel := getattr(voice, "channel")) is None:
            raise BotError('No voice channel.', 42, 'music')
        if self.ctx.voice_client:
            if self.is_playing:
                raise BotError(
                    'Already connected to voice channel.', 41, 'music')
            else:
                await self.ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        return channel

    async def teardown(self, guild: discord.Guild):
        if not self.is_connected:
            raise BotError('No voice channel.', 42, 'music')
        await guild.voice_client.disconnect(force=True)
        try:
            del self.music.players[guild.id]
        except KeyError:
            pass

    async def add_tracks(self, ctx, message, query):
        search = False
        playlist = False
        if re.match(URL_REGEX, query):
            tracks, playlist = await self.get_tracks(ctx, message, query)
            if isinstance(tracks, yt_dlp.DownloadError):
                raise BotError(
                    f"No tracks found:\n{tracks[0]}", 44, 'music')
            if playlist:
                return
        else:
            search = True
        if not search:
            track = tracks[0]
        else:
            if self.settings.multiquery:
                if isinstance(track := await self.choose_track(ctx, message, query), yt_dlp.DownloadError):
                    raise BotError(
                        "No tracks found:\n"+str(track), 44, 'music')
            else:
                if isinstance(track := await self.get_single_track(ctx, query), yt_dlp.DownloadError):
                    raise BotError(
                        "No tracks found:\n"+str(track), 44, 'music')
        self.queue.add(track)
        await message.edit(
            embed=get_default_embed(
                ctx=ctx,
                title=f'Queued **{track.title}**   ({from_seconds_to_time_format(track.duration)})',
                url=track.url
            ).set_author(name=f'Track added successfully'),
            view=None
        )
        await self.get_to_playing(ctx)

    async def get_single_track(self, ctx, query):
        ytdl = include_playlist(self.settings.inplaylist)
        data = (await get_ytdl_data(self.loop, ytdl, query))[0]
        if isinstance(data, yt_dlp.DownloadError):
            return data
        return Track.from_data(ctx, data)

    async def choose_track(self, ctx: commands.Context, message: str, query: str):
        data = await get_prime_ytdl_data(self.loop, YTDL5, query)

        if isinstance(data, yt_dlp.DownloadError):
            return data

        try:
            data = data['entries']
        except KeyError:
            pass

        tracks: list[Track] = []
        for item in data:
            tracks.append(
                Track(
                    None,
                    "https://www.youtube.com/watch?v=" + item["id"],
                    item["title"] if 'title' in item.keys() else None,
                    item["duration"] if 'duration' in item.keys() else None,
                    None
                )
            )

        embed = get_default_embed(
            ctx=ctx,
            title=f"Choose a track by reacting or typing {self.prefix}<number>.",
            description="\n".join(
                f"`{i+1}.` [{track.title}]({track.url}) `({from_seconds_to_time_format(track.duration)})`" for i, track in enumerate(tracks)),
        ).set_author(name="Query results...", icon_url=self.bot.user.display_avatar.url)

        view = TrackChoosingView(len(tracks))

        await message.edit(embed=embed, view=view)

        def check(msg: discord.Message):
            return msg.author.id == ctx.author.id and re.match(PLAY_MESSAGE_REGEX, msg.content)

        tasks = [
            asyncio.create_task(view.wait(), name="button"),
            asyncio.create_task(self.bot.wait_for(
                "message", check=check), name="msg")
        ]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=30.0)
        if not done:
            raise BotError("No tracks found.", 44, 'music')
        else:
            finished = list(done)[0]
            if finished.get_name() == "button":
                indicator = view.value
            else:
                msg: discord.Message = finished.result()
                match = re.match(PLAY_MESSAGE_REGEX, msg.content)
                if not match or match.group(3):
                    raise BotError("No tracks found.", 44, 'music')
                indicator: int = int(match.group(2))-1
            view.children[indicator].emoji = "✔️"
            view.children[indicator].style = 3
            await message.edit(view=view)
            track = Track.from_data(ctx, (await get_ytdl_data(self.loop, YTDL, tracks[indicator].url))[0])
            return track

    async def get_tracks(self, ctx, message, query):
        ytdl = include_playlist(self.settings.inplaylist)
        data = await get_prime_ytdl_data(self.loop, ytdl, query)
        if isinstance(data, yt_dlp.DownloadError):
            return data, None
        playlist = False
        tracks: list[Track] = []
        if 'entries' in data:
            data = data['entries']
            playlist = True
            urls = ["https://www.youtube.com/watch?v="+item["id"]
                    for item in data]
            await self.multiplayfunc(ctx, message, None, urls)
        else:
            tracks.append(Track.from_data(ctx, data))
        return (tracks, playlist)

    async def multi_tracks(self, ctx: commands.Context, queries):
        tracks: list[Track] = []
        failure_count = 0
        ytdl = include_playlist(self.settings.inplaylist)
        datas = await get_multiple_ytdl_data(self.loop, ytdl, queries)
        for video_data in datas:
            if isinstance(video_data, yt_dlp.DownloadError):
                failure_count += 1
                continue
            tracks.append(Track.from_data(ctx, video_data))
        return (tracks, failure_count)

    async def multiplayfunc(self, ctx, message, name, queries):
        tracks, failure_count = await self.multi_tracks(ctx, queries)
        length = len(tracks)
        self.queue.add(*tracks)
        embed = get_default_embed(ctx)
        if name:
            embed.title = f'Queued {f"**{length}** tracks" if length > 1 else "**1** track"} from playlist **{name}**.' + (
                f" [FAILURES: **{failure_count}**]" if failure_count > 0 else "")
        else:
            embed.title = f'Multiqueued a list of {f"**{length}** tracks" if length > 1 else f"**{length}** track"}' + (
                f" [FAILURES: **{failure_count}**]" if failure_count > 0 else "")
        embed.description = "\n".join(
            f"`{i+1}.` [{track.title}]({track.url}) `({from_seconds_to_time_format(track.duration)})`" for i, track in enumerate(tracks[:5]))
        if length > 5:
            embed.description += f"\n`...` _and another_ {'**'+str(length-5)+'** _tracks' if length > 6 else '**1** _track'}._"
        embed.set_author(name="Music found.",
                         icon_url=self.bot.user.display_avatar.url)
        await message.edit(embed=embed)
        await self.get_to_playing(ctx)

    def make_source(self, source, start_seconds):
        return CalculableAudio(
            discord.FFmpegPCMAudio(
                source,
                options="-vn -loglevel quiet -hide_banner -nostats",
                before_options=f"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 0 -nostdin -ss {start_seconds}"
            ),
            start_seconds*1000,
            self.volume
        )

    async def get_to_playing(self, ctx):
        if not self.is_playing and not self.is_paused:
            try:
                self.start_playback(ctx)
            except discord.errors.ClientException:
                try:
                    await self.connect(ctx)
                    self.start_playback(ctx)
                except BotError:
                    await self.teardown(ctx.guild)

    def change_volume(self, vol: int):
        vol = vol/100
        if not self.queue.is_empty:
            self.ctx.voice_client.source.volume = vol
        self.volume = vol

    def seek(self, secs: int):
        track = self.queue.current_track
        duration = track.duration
        if secs >= duration:
            secs = duration - 1
        elif secs < 0:
            secs = 0
        self.ctx.voice_client.source = self.make_source(
            source=track.source, start_seconds=secs)
        return track, secs

    def stop(self):
        self.queue.empty()
        self.queue.empty_history()
        self.ctx.voice_client.stop()

    def skip(self, force=False, tf=True):
        if not force:
            try:
                track = self.queue.current_track
                self.ctx.voice_client.stop()
                return track
            except BotError as e:
                if e.code == 43:
                    return None
                else:
                    raise e
        else:
            self.ctx.voice_client.stop()

    def pause(self):
        try:
            track = self.queue.current_track
            self.ctx.voice_client.pause()
            return track
        except BotError as e:
            if e.code == 43:
                return None
            else:
                raise e

    def resume(self):
        try:
            track = self.queue.current_track
            self.ctx.voice_client.resume()
            return track
        except BotError as e:
            if e.code == 43:
                return None
            else:
                raise e

    def start_playback(self, ctx):
        self.ctx.voice_client.play(self.make_source(
            self.queue.current_track.source, 0), after=lambda error: self.check_queue(error, ctx))

    async def autoplay_next_track(self, ctx: commands.Context):
        track: Track = self.queue._history[-1]
        url: str = track.url
        if not url.startswith('https://www.youtube.com/watch?v='):
            raise BotError(
                'Autoplay Error: Unable to fetch video from non-youtube url.', 45, 'music')
        video_id = url[32:]
        message = await ctx.send(embed=get_default_embed(ctx=ctx, title='Autoplaying new track...'))
        new_url = await get_autoplay_video(video_id=video_id, video_title=track.title)
        if not new_url:
            raise BotError(
                'Autoplay Error: Unable to find related video.', 45, 'music')
        await self.add_tracks(ctx, message, new_url)

    def check_queue(self, error: Exception, ctx: commands.Context):
        if error:
            error = getattr(error, 'original', error)

            embed = get_default_embed(
                ctx=ctx,
                title=f"Failure executing {ctx.hybrid_command if ctx.hybrid_command else ''} hybrid_command:",
                color=discord.Colour.red()
            ).set_author(
                name=f"An Error Occured!",
                icon_url=self.bot.user.display_avatar.url
            ).add_field(
                name="Details:",
                value=f"{error}",
                inline=False
            )

            print('Ignoring exception in hybrid_command {}:'.format(
                ctx.hybrid_command), file=sys.stderr)
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr)

            asyncio.run_coroutine_threadsafe(ctx.send(embed=embed), self.loop)
        try:
            try:
                if self.ctx.voice_client.source.played <= 20:
                    self.queue.current_track.source = YTDL.extract_info(
                        self.queue.current_track.url, download=False)['url']
                    return self.start_playback(ctx)
            except AttributeError:
                pass
            if self.queue.get_next_track() is not None:
                self.start_playback(ctx)
            else:
                if self.settings.autoplay:
                    asyncio.run_coroutine_threadsafe(
                        self.autoplay_next_track(ctx), self.loop)
                else:
                    asyncio.run_coroutine_threadsafe(
                        self.finish_playing(ctx), self.loop)
        except (BotError, AttributeError):
            asyncio.run_coroutine_threadsafe(
                self.finish_playing(ctx), self.loop)

    async def finish_playing(self, ctx):
        if self.schedule_member:
            for member in self.schedule_member:
                await member.move_to(channel=None)
            await ctx.send(
                embed=get_default_embed(
                    ctx=ctx,
                    title="**Disconnected these members:**",
                    description="\n".join(
                        member for member in self.schedule_member),
                )
            )
            self.schedule_member.clear()


class MusicContainer(object):
    def __init__(self, cog: commands.Cog):
        self.players: dict[int, MusicPlayer] = {}
        self.cog = cog

    def create_player(self, ctx: commands.Context):
        player = MusicPlayer(ctx, self)
        self.players[ctx.guild.id] = player
        return player

    def get_player(self, guild_id: int):
        try:
            return self.players[guild_id]
        except KeyError:
            return None


class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music = MusicContainer(self)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        if (player := self.music.get_player(member.guild.id)) is None or not member.guild.voice_client:
            return
        if member.guild.voice_client.channel != before.channel:
            return
        if after.channel != member.guild.voice_client.channel:
            for m in before.channel.members:
                if not m.bot:
                    return
            time = 0
            while time < 60:
                for m in member.guild.get_channel(before.channel.id).members:
                    if m.bot:
                        continue
                    return
                await asyncio.sleep(0.98)
                time += 1
            await player.teardown(member.guild)

    async def connecter(self, ctx: commands.Context, tf=False):
        if (player := self.music.get_player(ctx.guild.id)) is None:
            player = self.music.create_player(ctx)
        try:
            channel = await player.connect(ctx)
            if isinstance(channel, discord.StageChannel):
                await ctx.me.edit(suppress=False)
            return channel, player
        except BotError as e:
            if e.code != 41 or tf:
                raise e
            else:
                return None, player

    @commands.hybrid_command(name="join", aliases=['connect', 'con'])
    async def join_command(self, ctx: commands.Context):
        """
        Connects to the voice channel you're in.

        Gets the bot to connect to the voice channel that you're currently in.
        """
        channel, _ = await self.connecter(ctx, True)
        if channel:
            return await ctx.send(embed=get_default_embed(ctx=ctx, title=f"**Connected to {channel}.**"))

    @commands.hybrid_command(name='leave', aliases=['disconnect', 'dis'])
    async def leave_command(self, ctx: commands.Context):
        """
        Disconnects from the current channel.

        Gets the bot to disconnect from the voice channel that it is currently in.
        This will clear everything related to music, e.g: queue, tracks, history,...
        """
        if not ctx.voice_client:
            raise BotError('No voice channel.', 42, 'music')
        if (player := self.music.get_player(ctx.guild.id)) is None:
            await ctx.voice_client.disconnect(force=True)
        else:
            await player.teardown(ctx.guild)
        return await ctx.send(embed=get_default_embed(ctx=ctx, title="**Left voice channel.**"))

    @commands.hybrid_command(name='url', aliases=['urls'])
    async def url_command(self, ctx: commands.Context):
        """
        Extracts all the urls of the current queue.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        trackurls = [track.url + '\n' for track in player.current_queue]
        f = StringIO()
        f.writelines(trackurls)
        f.seek(0)
        file = discord.File(fp=f, filename='queue_urls.txt')
        await ctx.send(file=file)
        f.close()

    @commands.command(name='schebreak', aliases=['sche'])
    async def scheduled_break_command(self, ctx: commands.Context, *members: discord.Member):
        """
        Adding members to schedule break list.

        When the player ends, automatically disconnects members in schedule break list.

        <*members> : one or more members to add to schedule break list.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if not members:
            return await ctx.send(
                embed=get_default_embed(
                    ctx=ctx,
                    title="**Members in schedule break lists:**",
                    description="\n".join(member.mention for member in player.schedule_member) if len(player.schedule_member) <= 20 else (
                        "\n".join(member.mention for member in player.schedule_member[:20])+"\nAnd more...")
                )
            )
        for member in members:
            if not member in player.schedule_member:
                player.schedule_member.append(member)
        return await ctx.send(
            embed=get_default_embed(
                title="**Added these members to schedule break list:**",
                description="\n".join(member.mention for member in members) if len(members) <= 20 else (
                    "\n".join(member.mention for member in members[:20])+"\nAnd more...")
            )
        )

    @commands.hybrid_command(name='play', aliases=['p'])
    @app_commands.describe(
        query='The url or title to search for.'
    )
    async def play_command(self, ctx: commands.Context, *, query: str):
        """
        Plays a track from url or query.

        If the input query is the title or the name of the track, searches on youtube for 5 tracks that match the title.
        If you want an instant search, you can toggle the "multitrack" hybrid_command off to get only the first track that matches the title.
        
        If the input query is an url, automatically queues the track from the source.
        Supported websites: https://ytdl-org.github.io/youtube-dl/supportedsites.html
        """
        if query in ['1', '2', '3', '4', '5']:
            return
        _, player = await self.connecter(ctx)
        if not player:
            return
        message = await ctx.send(embed=get_default_embed(ctx=ctx, title="Fetching data..."))
        try:
            await player.add_tracks(ctx, message, query)
        except BotError as e:
            if e.code == 44:
                await message.delete()
            raise e

    @commands.command(name='multiplay', aliases=['mp', 'mplay'])
    async def multiplay_command(self, ctx: commands.Context, *queries: str):
        """
        Multiqueue tracks base on urls.

        <*queries> : a list of queries to queue (url only)
        """
        channel, player = await self.connecter(ctx)
        if not channel and not player:
            return
        message = await ctx.send(embed=get_default_embed(ctx=ctx, title="Fetching data..."))
        await player.multiplayfunc(ctx, message, None, queries)

    @commands.hybrid_group(name="playlist", aliases=['pl'], case_insensitive=True)
    async def playlist_command(self, ctx: commands.Context):
        """
        A group of commands related to playlist.

        If no subcommand is invoked, returns a list of playlists.
        """
        if ctx.invoked_subcommand is None:
            await self.pshow_command(ctx)

    @playlist_command.command(name="export", aliases=['exp', 'ex'])
    @app_commands.describe(
        name='The name of the playlist.'
    )
    async def pexport_command(self, ctx: commands.Context, *, name: str):
        """
        Exports the current queue to a playlist for later.

        Exports a playlist with the name <name>. Later can be queued back using the "playlist play <name>" hybrid_command.
        If a playlist named <name> already exists, the author of the playlist can overwrite the playlist, others cannot do this.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        find = DB.find_one(
            {"_id": ctx.guild.id},
            {f"playlists.{name}": 1}
        )
        if find and find.get('playlists', None):
            find = find['playlists']
            if find['plauthor'] == ctx.author.id or self.bot.is_owner(ctx.author):
                view = Confirm(ctx.author)
                message = await ctx.send(
                    embed=get_default_embed(
                        ctx=ctx,
                        title=f'**Your playlist called {name} already existed, do you want to overwrite it?**'
                    ),
                    view=view
                )
                timeout = await view.wait()
                if timeout:
                    await ctx.message.delete()
                    return await message.delete()
                if view.value:
                    await message.delete()
                else:
                    await ctx.message.delete()
                    return await message.delete()
            else:
                return await ctx.send(
                    embed=get_default_embed(
                        ctx=ctx,
                        title=f"The playlist called {name} already existed, to change this playlist you need permissions from its author."
                    )
                )

        tracks = player.current_queue
        trackurl = []
        trackname = []
        trackduration = []
        for track in tracks:
            trackurl.append(track.url)
            trackname.append(track.title)
            trackduration.append(track.duration)

        newplaylist = {
            "trackurls": trackurl,
            "tracknames": trackname,
            "trackdurations": trackduration,
            "plauthor": ctx.author.id
        }
        DB.update_one(
            {'_id': ctx.guild.id},
            {"$set": {f"playlists.{name}": newplaylist}},
            upsert=True
        )
        length = len(trackurl)
        embed = get_default_embed(
            ctx=ctx,
            title=f'Exported playlist **{name}** containing {f"**{length}** tracks" if length > 1 else f"**{length}** track"}.',
            description="\n".join(
                f"`{i+1}.` [{track.title}]({track.url}) `({from_seconds_to_time_format(track.duration)})`" for i, track in enumerate(tracks[:5])),
        ).set_author(
            name=f"Use ..playplist play {name} to play the playlist.",
            icon_url=self.bot.user.display_avatar.url
        )
        if length > 5:
            embed.description += f"\n`...` _and another_ {'**'+str(length-5)+'** _tracks' if length > 6 else '**1** _track'}._"
        await ctx.send(embed=embed)

    @playlist_command.command(name="play", aliases=['p'])
    @app_commands.describe(
        name='The name of the playlist.'
    )
    async def pplay_command(self, ctx: commands.Context, *, name: str):
        """
        Plays a playlist with the input name.

        Plays a playlist with the name <name>, if exists.
        """
        find = DB.find_one(
            {"_id": ctx.guild.id},
            {f"playlists.{name}": 1}
        )
        if not find or not find.get('playlists', None):
            raise BotError(
                f"The playlist named {name} is invalid.", 46, 'music')
        find = find['playlists'][name]['trackurls']
        channel, player = await self.connecter(ctx)
        if not channel and not player:
            return
        message = await ctx.send(embed=get_default_embed(ctx=ctx, title="Fetching data..."))
        await player.multiplayfunc(ctx, message, name, find)

    @playlist_command.command(name="shuffle", aliases=['sh'])
    @app_commands.describe(
        name='The name of the playlist.'
    )
    async def pshuffle_command(self, ctx: commands.Context, *, name: str):
        """
        Plays and shuffles a playlist with the input name.

        Plays and shuffles a playlist with the name <name>, if exists.
        """
        find = DB.find_one(
            {"_id": ctx.guild.id},
            {f"playlists.{name}": 1}
        )
        if not find or not find.get('playlists', None):
            raise BotError(
                f"The playlist named {name} is invalid.", 46, 'music')
        find = find['playlists'][name]['trackurls']
        channel, player = await self.connecter(ctx)
        if not channel and not player:
            return
        message = await ctx.send(embed=get_default_embed(ctx=ctx, title="Fetching data..."))
        random.shuffle(find)
        await player.multiplayfunc(ctx, message, name, find)

    @playlist_command.command(name="remove", aliases=['del', 'rm', 'delete'])
    @app_commands.describe(
        name='The name of the playlist.'
    )
    async def premove_command(self, ctx: commands.Context, *, name: str):
        """
        Remove a saved playlist.

        Arguments:
            <name>: The name of the playlist.
        """
        find = DB.find_one(
            {"_id": ctx.guild.id},
            {f"playlists.{name}": 1}
        )
        if not (find and find.get('playlists', None)):
            raise BotError(
                f"The playlist named ***{name}*** is invalid.", 46, 'music')
        find = find['playlists'][name]
        if find['plauthor'] == ctx.author.id or self.bot.is_owner(ctx.author):
            view = Confirm(ctx.author)
            message = await ctx.send(
                embed=get_default_embed(
                    ctx=ctx,
                    title=f'**Do you actually want to delete the playlist ***{name}***?**'
                ),
                view=view
            )
            timeout = await view.wait()
            if timeout:
                await ctx.message.delete()
                return await message.delete()
            if view.value:
                await message.delete()
            else:
                await ctx.message.delete()
                return await message.delete()
        else:
            return await ctx.send(
                embed=get_default_embed(
                    ctx=ctx,
                    title=f"To delete this playlist you need permissions from its author."
                )
            )
        DB.update_one({'_id': ctx.guild.id}, {
            "$unset": {f"playlists.{name}": ""}}, upsert=True)
        await ctx.send(embed=get_default_embed(ctx=ctx, title=f"Deleted the playlist named *{name}*."))

    @playlist_command.command(name="show")
    @app_commands.describe(
        name='The name of the playlist to show.'
    )
    async def pshow_command(self, ctx: commands.Context, *, name: str = None):
        """
        Returns one playlist or a list of playlists.

        Shows one or every playlist saved in the guild.
        """
        find = DB.find_one(
            {"_id": ctx.guild.id},
            {f"playlists": 1}
        )
        if not find or not find.get('playlists', None):
            raise BotError(
                f"The guild currently has no playlists.", 46, 'music')
        find = find['playlists']
        if name == None:
            find = list(find.keys())
            length = len(find)
            pagelist = (length-1)//20 + 1
            if pagelist <= 0:
                pagelist = 1
            embedlist = []
            for i in range(pagelist):
                embed = get_default_embed(
                    ctx=ctx,
                    title=f"There are {length} playlists saved: " if length > 1 else f"There is {length} playlist saved: ",
                    description="```\n" +
                    f"\n``````\n".join(
                        name for name in find[i*20:i*20+20]) + "\n```"
                ).set_author(
                    name=f"Page {i+1}/{pagelist}.",
                    icon_url=self.bot.user.display_avatar.url
                )
                embedlist.append(embed)
            if pagelist <= 1:
                return await ctx.send(embed=embedlist[0])
            view = Pagelist(embedlist, timeout=180.0)
            message = await ctx.send(embed=embedlist[0], view=view)
            timeout = await view.wait()
            if timeout:
                return await message.edit(view=None)
        else:
            if not name in find:
                raise BotError(
                    f"The playlist named {name} is invalid.", 46, 'music')
            find = find[name]
            user = self.bot.get_user(find['plauthor'])
            length = len(find['trackurls'])
            pagelist = (length-1)//5 + 1
            if pagelist <= 0:
                pagelist = 1
            embedlist = []
            for i in range(pagelist):
                embed = get_default_embed(
                    ctx=ctx,
                    title=f"Playlist {name} has {length} {'tracks' if length > 1 else 'track'}:",
                    description="\n".join(
                        f"`{j+1}.` [{find['tracknames'][j]}]({find['trackurls'][j]}) `({from_seconds_to_time_format(find['trackdurations'][j])})`" for j in range(i*5, min(i*5+5, length))),
                ).set_author(
                    name=f"Page {i+1}/{pagelist}. (Author: {user})",
                    icon_url=self.bot.user.display_avatar.url
                )
                embedlist.append(embed)
            if pagelist <= 1:
                return await ctx.send(embed=embedlist[0])
            view = Pagelist(embedlist, timeout=30.0)
            message = await ctx.send(embed=embedlist[0], view=view)
            timeout = await view.wait()
            if timeout:
                return await message.edit(view=None)

    @playlist_command.command(name="url", aliases=['urls', 'uri'])
    @app_commands.describe(
        name='The name of the playlist to show urls.'
    )
    async def purl_command(self, ctx, *, name: str):
        """
        Returns all tracks' urls of a playlist.

        Shows all the tracks' urls of the playlist that matches the name.
        """
        find = DB.find_one(
            {"_id": ctx.guild.id},
            {f"playlists.{name}": 1}
        )
        if not find:
            raise BotError(
                f"The playlist named {name} is invalid.", 46, 'music')
        find = find['playlists'][name]
        trackurls = '\n'.join(find['trackurls'])
        f = StringIO()
        f.writelines(trackurls)
        f.seek(0)
        file = discord.File(fp=f, filename='queue_urls.txt')
        await ctx.send(file=file)
        f.close()

    @commands.hybrid_command(name='pause', aliases=['ps'])
    async def pause_command(self, ctx: commands.Context):
        """
        Pauses the currently playing track.

        Pauses the playing track, use "resume" hybrid_command to continue the playback.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        track = player.pause()
        if track:
            await ctx.send(
                embed=get_default_embed(
                    ctx=ctx,
                    title=f"**{track.title}** is paused."
                )
            )
        else:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')

    @commands.hybrid_command(name='resume', aliases=['unp', 'unpause'])
    async def resume_command(self, ctx: commands.Context):
        """
        Resumes the playback, if paused.

        Resumes the playback if it was paused earlier.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        track = player.resume()
        if track:
            await ctx.send(
                embed=get_default_embed(
                    ctx=ctx,
                    title=f"**{track.title}** is resumed."
                )
            )
        else:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')

    @commands.hybrid_command(name='skip', aliases=['next', 's', 'skipto'])
    @app_commands.describe(
        position='The index of the track in the upcoming list to skip to.'
    )
    async def skip_command(self, ctx: commands.Context, position: Optional[int] = None):
        """
        Skips one or more playing tracks.

        Skips once if nothing is passed in else skips to the track in <place>.
        This hybrid_command will not remove the track when the repeat mode is set to ALL.
        If you want to remove a particular track, try the "remove" hybrid_command instead.

        Arguments:
            <place> : The index of the track in the upcoming list to skip to.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if not position or position < 1:
            track = player.skip()
            if track:
                await ctx.send(
                    embed=get_default_embed(
                        ctx=ctx,
                        title=f"**{track.title}** is skipped."
                    )
                )
            else:
                raise BotError(
                    "Nothing is being played at the moment.", 43, 'music')
        else:
            if player.queue.repeat_mode == RepeatMode.ONE:
                return await ctx.send(
                    embed=get_default_embed(
                        ctx=ctx,
                        title="You can't use this hybrid_command when repeat mode is set to ONE.",
                    )
                )
            track = player.queue.get_to_track(position)
            _ = player.skip()
            await ctx.send(
                embed=get_default_embed(
                    ctx=ctx,
                    title=f"Skipped to {track.title}."
                )
            )

    @commands.hybrid_command(name="recycle", aliases=['recy', 'restore', 'prev', 'previous'])
    @app_commands.describe(
        positions='The indexes of tracks in history to recycle.'
    )
    async def recycle_command(self, ctx: commands.Context, *, positions: str = None):
        """
        Recycles one or more tracks in history.

        Recycles back to the latest song in history if nothing is passed in else recycles tracks whose indexes in history matches <*positions>.
        This hybrid_command will not remove the track when the repeat mode is set to ALL.
        If you want to remove a particular track, try the "remove" hybrid_command instead.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "No previous track found in history.", 44, 'music')
        if not player.queue._history:
            raise BotError(
                "No previous track found in history.", 44, 'music')
        if not positions:
            positions = [len(player.queue._history)]
        else:
            positions = positions.split()
            try:
                positions = [int(position) for position in positions]
            except ValueError:
                raise commands.BadArgument('Positions must be integer.')
        tracks, tf = player.queue.get_multiple_previous_tracks(positions)
        if not tracks:
            raise BotError(
                "Could not find any track that matches.", 44, 'music')
        if tf:
            ctx.voice_client.source = player.make_source(
                player.queue.current_track.source, 0)
        else:
            await player.get_to_playing(ctx)
        embedlist = []
        length = len(tracks)
        pagelist = (length-1)//5+1
        if pagelist <= 0:
            pagelist = 1
        for i in range(pagelist):
            embed = get_default_embed(
                ctx=ctx,
                title=f"Recycled {length} {'tracks' if length > 1 else 'track'} from history:",
                description="\n".join(
                    f"`{(j+1)+i*5}.` [{track.title}]({track.url}) `({from_seconds_to_time_format(track.duration)})` added by **@{self.bot.get_user(track.requester_id)}**." for j, track in enumerate(tracks[i*5:i*5+5])),
            ).set_author(
                name=f"Page {i+1}/{pagelist}.",
                icon_url=self.bot.user.display_avatar.url
            )
            embedlist.append(embed)
        if pagelist <= 1:
            return await ctx.send(embed=embedlist[0])
        view = Pagelist(embedlist, timeout=30.0)
        message = await ctx.send(embed=embedlist[0], view=view)
        timeout = await view.wait()
        if timeout:
            return await message.edit(view=None)

    @commands.hybrid_command(name="remove", aliases=['delete', 'del'])
    @app_commands.describe(
        positions='The indexes of tracks in the [upcoming] queue to remove.'
    )
    async def remove_command(self, ctx: commands.Context, *, positions: str = None):
        """
        Remove a track in queue.

        Completely erases the existence of a track in queue.
        Tracks erased by this hybrid_command will not appear in history.
        If no index is passed in, will erase the currently playing track.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError("No tracks found.", 44, 'music')
        if not positions:
            positions = [0]
        else:
            positions = positions.split()
            try:
                positions = [int(position) for position in positions]
            except ValueError:
                raise commands.BadArgument('Positions must be integer.')
        tracks = player.queue.remove_multiple_tracks(positions)
        if not tracks:
            raise BotError(
                "Could not remove any track that matches.", 44, 'music')
        if 0 in positions:
            if player.queue.current_track:
                ctx.voice_client.source = player.make_source(
                    source=player.queue.current_track.source, start_seconds=0)
            else:
                player.skip(force=True)
        embedlist = []
        length = len(tracks)
        tracks.reverse()
        pagelist = (length-1)//5+1
        if pagelist <= 0:
            pagelist = 1
        for i in range(pagelist):
            embed = get_default_embed(
                ctx=ctx,
                title=f"Remove {length} {'tracks' if length > 1 else 'track'} from queue:",
                description="\n".join(
                    f"`{(j+1)+i*5}.` [{track.title}]({track.url}) `({from_seconds_to_time_format(track.duration)})` added by **@{self.bot.get_user(track.requester_id)}**." for j, track in enumerate(tracks[i*5:i*5+5]))
            ).set_author(
                name=f"Page {i+1}/{pagelist}.",
                icon_url=self.bot.user.display_avatar.url
            )
            embedlist.append(embed)
        if pagelist <= 1:
            return await ctx.send(embed=embedlist[0])
        view = Pagelist(embedlist, timeout=30.0)
        message = await ctx.send(embed=embedlist[0], view=view)
        timeout = await view.wait()
        if timeout:
            return await message.edit(view=None)

    @commands.hybrid_command(name='stop', aliases=['st'])
    async def stop_command(self, ctx: commands.Context):
        """
        Stops the playback.

        Stops the playback and erases everything including tracks in the current queue and in history.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        player.stop()
        await ctx.send(embed=get_default_embed(ctx=ctx, title=f"**Stopped playing.**"))

    @commands.hybrid_command(name="restart", aliases=['res'])
    async def restart_command(self, ctx: commands.Context):
        """
        Restarts the currently playing track.

        Gets to the start of the currently playing track, if playback is paused, will resume the playback.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        track, _ = player.seek(0)
        await ctx.send(embed=get_default_embed(ctx=ctx, title=f"Restarted **{track.title}**."))

    @commands.hybrid_command(name="seek")
    @app_commands.describe(
        time='The time to seek.'
    )
    async def seek_command(self, ctx: commands.Context, time: str):
        """
        Seeks a position of the playing track.

        Seeks and go to the passed in timestamp of the track.
        If playback is paused, will resume the playback.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        secs = from_time_format_to_seconds(time)
        if not secs:
            raise commands.BadArgument(
                "Invalid timestamp, should be [[<h>:]<m>:]<s> or [[<h>h]<m>m]<s>s for hours, minutes and seconds respectively.")
        track, secs = player.seek(secs)
        await ctx.send(embed=get_default_embed(ctx=ctx, title=f"Seeked **{track.title}** at _{from_seconds_to_time_format(secs)}_."))

    @commands.hybrid_command(name="rewind", aliases=['rew', 'rwd'])
    @app_commands.describe(
        time='The amount of time to rewind.'
    )
    async def rewind_command(self, ctx: commands.Context, time: str):
        """
        Rewinds the playing track.

        Rewinds the currently playing track an amount of time given.
        If playback is paused, will resume the playback.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        secs = from_time_format_to_seconds(time)
        if not secs:
            raise commands.BadArgument(
                "Invalid timestamp, should be [[<h>:]<m>:]<s> or [[<h>h]<m>m]<s>s for hours, minutes and seconds respectively.")
        secs = ctx.voice_client.source.played//1000 - secs
        track, secs = player.seek(secs)
        await ctx.send(embed=get_default_embed(ctx=ctx, title=f"Rewinded **{track.title}** to _{from_seconds_to_time_format(secs)}_."))

    @commands.hybrid_command(name="forward", aliases=['frw', 'fwd'])
    @app_commands.describe(
        time='The amount of time to forward.'
    )
    async def forward_command(self, ctx: commands.Context, time: str):
        """
        Forwards the playing track.

        Forwards the currently playing track an amount of time given.
        If playback is paused, will resume the playback.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        secs = from_time_format_to_seconds(time)
        if not secs:
            raise commands.BadArgument(
                "Invalid timestamp, should be [[<h>:]<m>:]<s> or [[<h>h]<m>m]<s>s for hours, minutes and seconds respectively.")
        secs = ctx.voice_client.source.played//1000 + secs
        track, secs = player.seek(secs)
        await ctx.send(embed=get_default_embed(ctx=ctx, title=f"Forwarded **{track.title}** to _{from_seconds_to_time_format(secs)}_."))

    @commands.hybrid_command(name='nowplaying', aliases=['np'])
    async def nowplaying_command(self, ctx: commands.Context):
        """
        Shows info of the playing track.

        Shows the info of the currently playing track.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        track = player.queue.current_track
        await ctx.send(
            embed=get_default_embed(
                ctx=ctx,
                title=f'Now playing **{track.title}**   ({from_seconds_to_time_format(ctx.voice_client.source.played//1000)}/{from_seconds_to_time_format(track.duration)})',
                url=track.url
            ).set_author(name=f'Added by @{self.bot.get_user(track.requester_id)}')
        )

    @commands.hybrid_command(name='volume', aliases=['vol'])
    @app_commands.describe(
        vol="The volume to set the playback."
    )
    async def volume_command(self, ctx: commands.Context, vol: int):
        """
        Adjusts playback volume.

        Changes the playback volume according to the percentage passed in.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        player.change_volume(vol)
        return await ctx.send(embed=get_default_embed(ctx=ctx, title=f"Set player volume to {vol}%."))

    @commands.hybrid_command(name='set')
    @app_commands.describe(
        setting='The setting to toggle',
        value='The value to toggle the setting to.'
    )
    async def set_command(self, ctx: commands.Context, setting: str = None, value: bool = None):
        """
        Toggles a setting.

        If multitrack is on, when searching for a track will return 5 tracks with matching title.
        If multitrack is off, automatically queues the best match.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if setting is None or (val := getattr(player.settings, setting.lower(), None)) is None:
            valid_settings = player.settings.__dict__
            embed = get_default_embed(
                ctx=ctx,
                title="Here are the valid settings:",
                description="\n".join(
                    [f"**{key.upper()}** = ***{val}***" for key, val in valid_settings.items()]),
            )
            return await ctx.send(embed=embed)
        if value is None:
            value = not val
        setattr(player.settings, setting, value)
        return await ctx.send(embed=get_default_embed(ctx=ctx, title=f"{setting.upper()} has been set to {value}."))

    @commands.hybrid_command(name="lyrics", aliases=['lyr', 'ly', 'lyric'])
    @app_commands.describe(
        name='The name of the track whose playlist to search for.'
    )
    async def lyrics_command(self, ctx, *, name: Optional[str] = None):
        """
        Finds the lyrics.

        If nothing is passed in and the there are tracks in queue, searches for the lyrics of the currently playing track based on its title else find the lyrics of the name passed in.
        """
        if not name:
            if (player := self.music.get_player(ctx.guild.id)) is None:
                raise BotError(
                    "Nothing is being played at the moment.", 43, 'music')
            if player.queue.is_empty:
                raise BotError(
                    "Nothing is being played at the moment.", 43, 'music')
            name = player.queue.current_track.title
        async with aiohttp.request("GET", "https://some-random-api.ml/lyrics?title=" + name, headers={}) as r:
            if not 200 <= r.status <= 299:
                return await ctx.send(embed=get_default_embed(ctx=ctx, title="No lyrics were found :((."))
            data = await r.json()
        lyrics = data['lyrics'].split('\n')
        pagelist = (len(lyrics)-1)//25 + 1
        if pagelist <= 0:
            pagelist = 1
        embedlist = []
        for i in range(pagelist):
            embed = get_default_embed(
                ctx=ctx,
                title=f"**Lyrics for _{data['title']}_**:",
                description="***" + "\n".join(lyrics[i*25:i*25+25]) + "***",
                thumbnail=data["thumbnail"]["genius"]
            ).set_author(
                name=name,
                url=data['links']['genius'],
                icon_url=self.bot.user.display_avatar.url
            )
            embedlist.append(embed)
        if pagelist <= 1:
            return await ctx.send(embed=embedlist[0])
        view = Pagelist(embedlist, timeout=180.0)
        message = await ctx.send(embed=embedlist[0], view=view)
        timeout = await view.wait()
        if timeout:
            return await message.edit(view=None)

    @commands.hybrid_command(name="history", aliases=['his', 'h'])
    @app_commands.describe(
        page='The page number.'
    )
    async def history_command(self, ctx: commands.Context, page: int = 1):
        """
        Shows the tracks in history.

        Shows all the tracks played before and left in history.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        show = 10
        history = player.queue._history
        embedlist = []
        pagelist = (len(history)-1)//show + 1
        if pagelist <= 0:
            pagelist = 1
        page = min(max(page-1, 0), pagelist-1)
        for i in range(pagelist):
            embed = get_default_embed(
                ctx=ctx,
                title="Current queue:",
                description=f"`Showing up to {show} tracks in one page`\n\n"
            ).set_author(
                name=f"Page {i+1}/{pagelist}.",
                icon_url=self.bot.user.display_avatar.url
            )
            embed.description += "**History:**\n"
            if history:
                embed.description += "\n".join(
                    f"`{(j+1)+i*show}.` [{track.title}]({track.url}) `({from_seconds_to_time_format(track.duration)})` added by **@{self.bot.get_user(track.requester_id)}**." for j, track in enumerate(history[i*show:i*show+show]))
            else:
                embed.description += "[None](https://media-exp1.licdn.com/dms/image/C560BAQE2gJD7MvCa3g/company-logo_200_200/0/1519874321126?e=2159024400&v=beta&t=Jx-k_A2GCJhG5unotwPmVJtBUPYmYptooyz2pcH-YCc)"
            embedlist.append(embed)
        if pagelist <= 1:
            return await ctx.send(embed=embedlist[0])
        view = Pagelist(embedlist, timeout=30.0, page_number=page)
        message = await ctx.send(embed=embedlist[page], view=view)
        timeout = await view.wait()
        if timeout:
            return await message.edit(view=None)

    @commands.hybrid_command(name='queue', aliases=['q'])
    @app_commands.describe(
        page='The page number.'
    )
    async def queue_command(self, ctx, page: int = 1):
        """
        Shows the tracks in queue.

        Shows the currently playing track and the upcoming tracks in order.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if player.queue.is_empty:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        show = 10
        upcoming = player.queue.upcoming
        embedlist = []
        pagelist = (len(upcoming)-1)//show + 1
        if pagelist <= 0:
            pagelist = 1
        page = min(max(page-1, 0), pagelist-1)
        for i in range(pagelist):
            embed = get_default_embed(
                ctx=ctx,
                title="Current queue:" if player.queue.repeat_mode != RepeatMode.ALL else "Currently repeating this queue:",
                description=f"`Showing up to {show} tracks in one page`\n\n"
            ).set_author(
                name=f"Page {i+1}/{pagelist}.",
                icon_url=self.bot.user.display_avatar.url
            )
            embed.description += "**Now playing:**\n" + f"[{player.queue.current_track.title}]({player.queue.current_track.url}) added by **@{self.bot.get_user(player.queue.current_track.requester_id)}**." if player.queue.repeat_mode != RepeatMode.ONE else "**Now playing:**\n" + \
                f"[{player.queue.current_track.title}]({player.queue.current_track.url}) `(LOOPING)` added by **@{self.bot.get_user(player.queue.current_track.requester_id)}**."
            embed.description += "\n\n**Upcoming:**\n"
            if upcoming:
                embed.description += "\n".join(
                    f"`{(j+1)+i*show}.` [{track.title}]({track.url}) `({from_seconds_to_time_format(track.duration)})` added by **@{self.bot.get_user(track.requester_id)}**." for j, track in enumerate(upcoming[i*show:i*show+show]))
            else:
                embed.description += "[None](https://media-exp1.licdn.com/dms/image/C560BAQE2gJD7MvCa3g/company-logo_200_200/0/1519874321126?e=2159024400&v=beta&t=Jx-k_A2GCJhG5unotwPmVJtBUPYmYptooyz2pcH-YCc)"
            embedlist.append(embed)
        if pagelist <= 1:
            return await ctx.send(embed=embedlist[0])
        view = Pagelist(embedlist, timeout=30.0, page_number=page)
        message = await ctx.send(embed=embedlist[page], view=view)
        timeout = await view.wait()
        if timeout:
            return await message.edit(view=None)

    @commands.hybrid_command(name='shuffle', aliases=['sh'])
    async def shuffle_command(self, ctx: commands.Context):
        """
        Shuffle the upcoming tracks.

        Reorders the upcoming list in a random way.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        player.queue.shuffle()
        return await ctx.send(embed=get_default_embed(ctx=ctx, title="The queue has been shuffled."))

    @commands.hybrid_command(name='repeat', aliases=['rep', 'loop'])
    @app_commands.describe(
        mode='The repeat mode to set to.'
    )
    async def repeat_command(self, ctx: commands.Context, mode: Literal['all', 'one', 'none'] = None):
        """
        Sets the repeat mode.

        Sets the playback repeat mode.
        Modes:
            "all"  : repeat the current queue.
            "one"  : loop one track.
            "none" : not repeating.
        """
        if (player := self.music.get_player(ctx.guild.id)) is None:
            raise BotError(
                "Nothing is being played at the moment.", 43, 'music')
        if mode is None:
            if player.queue.repeat_mode not in [RepeatMode.ALL, RepeatMode.ONE]:
                mode = "all"
            else:
                mode = "none"
        mode = mode.lower()
        player.queue.set_repeat_mode(mode)
        await ctx.send(embed=get_default_embed(ctx=ctx, title=f"Set repeat mode to {mode.upper()}."))


async def setup(client):
    await client.add_cog(music(client))
