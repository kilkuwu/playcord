import re
import discord
from discord.ext import commands

from .constants import TIME_REGEX, USERS_DB
from discord.utils import _string_width


def get_default_embed(
        ctx: commands.Context,
        title: str = None,
        description: str = None,
        thumbnail=None,
        **kwargs,
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color(0x960000),
        **kwargs
    )
    embed.set_footer(icon_url=ctx.author.display_avatar.url,
                     text=f'Invoked by {ctx.author}')
    embed.set_thumbnail(url=thumbnail)
    return embed


def get_max_size(strings):
    as_lengths = (_string_width(string) for string in strings)
    return max(as_lengths, default=0)


def format_api_arguments(bef_url: str, **kwargs):
    res = bef_url
    for key, val in kwargs.items():
        res += f"{key}={val}&"
    return res.replace(' ', '%20')


def from_time_format_to_seconds(time: str):
    if not (match := re.match(TIME_REGEX, time)):
        return None
    if match.group(1):
        position = int(match.group(1))
    elif match.group(2):
        position = int(match.group(2))*60
        if match.group(3):
            position += int(match.group(3))
    else:
        position = int(match.group(4))*60*60
        if match.group(5):
            position += int(match.group(5))*60
        if match.group(6):
            position += int(match.group(6))
    return position


def from_seconds_to_time_format(s):
    if s is None:
        return None
    s = int(s)
    total_msec = s * 1000
    total_seconds = s
    total_minutes = s / 60
    total_hours = s / 3600
    msec = int(total_msec % 1000)
    sec = int(total_seconds % 60 - (msec / 3600000))
    mins = int(total_minutes % 60 - (sec / 3600) - (msec / 3600000))
    hours = int(total_hours - (mins / 60) - (sec / 3600) - (msec / 3600000))
    return "{:02d}:{:02d}:{:02d}".format(hours, mins, sec) if hours > 0 else "{:02d}:{:02d}".format(mins, sec)
