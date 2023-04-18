import asyncio
import discord
from discord.ext import commands
import aiohttp
from json import JSONDecodeError
from utils.functions import format_api_arguments
import random


class nsfw(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='rule34', aliases=['r34'])
    @commands.is_nsfw()
    async def rule34_command(self, ctx: commands.Context, times: int, *, tags: str):
        """Fetch rule34 for posts."""
        times = min(times, 1000)
        times = max(times, 1)
        tags = tags.split()
        url = format_api_arguments(
            "https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&",
            times=times,
            tags=" ".join(tags),
        )
        message = await ctx.reply(content="Processing input...", mention_author=False)
        try:
            async with aiohttp.ClientSession() as session:
                responses = await (await session.get(url)).json()
        except JSONDecodeError:
            return await message.edit(content='Nothing was found.')
        await message.edit(content='Finished fetching.')
        info = []
        length = len(responses)
        for i in range(0, length, 3):
            pack = []
            for j in range(i, min(i+3, length)):
                pack.append([responses[j]['id'], responses[j]['file_url']])
            info.append(pack)

        for pack in info:
            content = f"Tags: `{'`, `'.join(tags)}`\n"
            view = discord.ui.View()
            for i, item in enumerate(pack):
                original = f"https://rule34.xxx/index.php?page=post&s=view&id={item[0]}"
                view.add_item(discord.ui.Button(
                    label=f"Original[{i+1}]", url=original))
                content += item[1]+'\n'
            await ctx.reply(content=content, view=view, mention_author=False)
            await asyncio.sleep(1)
        
    @commands.command(name='rule34shuffle', aliases=['r34s'])
    @commands.is_nsfw()
    async def rule34_shuffle_command(self, ctx: commands.Context, times: int, *, tags: str):
        """Fetch rule34 for posts."""
        times = min(times, 1000)
        times = max(times, 1)
        tags = tags.split()
        url = format_api_arguments(
            "https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&",
            times=times,
            tags=" ".join(tags),
        )
        message = await ctx.reply(content="Processing input...", mention_author=False)
        try:
            async with aiohttp.ClientSession() as session:
                responses = await (await session.get(url)).json()
        except JSONDecodeError:
            return await message.edit(content='Nothing was found.')
        random.shuffle(responses)
        await message.edit(content='Finished fetching.')
        info = []
        length = len(responses)
        for i in range(0, length, 3):
            pack = []
            for j in range(i, min(i+3, length)):
                pack.append([responses[j]['id'], responses[j]['file_url']])
            info.append(pack)

        for pack in info:
            content = f"Tags: `{'`, `'.join(tags)}`\n"
            view = discord.ui.View()
            for i, item in enumerate(pack):
                original = f"https://rule34.xxx/index.php?page=post&s=view&id={item[0]}"
                view.add_item(discord.ui.Button(
                    label=f"Original[{i+1}]", url=original))
                content += item[1]+'\n'
            await ctx.reply(content=content, view=view, mention_author=False)
            await asyncio.sleep(1)

    @commands.command(name='3d')
    @commands.is_nsfw()
    async def _3dnsfw_command(self, ctx: commands.Context, times: int = 10):
        """Fetch rule34 for 3d videos."""
        tags = "3d video sound score:>=1100"
        await self.rule34_command(ctx, times, tags=tags)


async def setup(client):
    await client.add_cog(nsfw(client))
