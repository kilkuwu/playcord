from datetime import timedelta
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Optional
import os
from pymongo import MongoClient
from utils.classes import BotError
from utils.functions import from_seconds_to_time_format, from_time_format_to_seconds
from utils.constants import DB as db

class miscellaneous(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.muted_member_roles = {}

    @commands.hybrid_command(name='clear', aliases=['clr'])
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        times='The number of message to clear.',
        member='The member whose message to clear.'
    )
    async def clear_command(self, ctx: commands.Context, times=1, member: discord.Member = None):
        """
        Clears n messages in the channel.

        This command requires you to have manage messages permission to execute.
        """
        if ctx.author.guild_permissions.administrator == True:
            if member == None:
                messages = await ctx.channel.purge(limit=times + 1)
                await ctx.send(embed=discord.Embed(title=f"Deleted {len(messages)-1} messages.", color=discord.Color.red()))
            else:
                messages = []
                async for message in ctx.channel.history(limit=times + 1):
                    if message.author == member:
                        messages.append(message)
                await ctx.channel.delete_messages(messages)
                await ctx.send(embed=discord.Embed(title=f"Deleted {len(messages)} messages of {member}.", color=discord.Color.red()))
        else:
            raise BotError(
                "You have to be an administrator to use this command.", 31, 'miscellaneous')

    @commands.hybrid_command(name='timeout')
    @app_commands.describe(
        member='The member to timeout.',
        time='The timeout time.',
        reason='The reason for this timeout.'
    )
    @commands.has_permissions(moderate_members=True)
    async def timeout_command(self, ctx: commands.Context, member: discord.Member, time: str = '1h', *, reason: Optional[str] = "No reason was provided"):
        """
        Timeout a member.

        This command requires you to have moderate members permission to execute.
        """
        await member.timeout(timedelta(seconds=from_time_format_to_seconds(time)), reason=reason)
        await ctx.send(embed=discord.Embed(title=f"**{member.display_name}** _is timed out by_ {ctx.author.display_name} for {time}.", description=f"**Reason:**\n*{reason}*", color=discord.Color.red()))

    @commands.hybrid_command(name='untimeout')
    @app_commands.describe(
        member='The member to untimeout.',
        reason='The reason for this untimeout.'
    )
    @commands.has_permissions(moderate_members=True)
    async def untimeout_command(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = "No reason was provided"):
        """
        Untimeout a member.

        This command requires you to have moderate members permission to execute.
        """
        await member.timeout(None, reason=reason)
        await ctx.send(embed=discord.Embed(title=f"**{member.display_name}** _is untimed out by_ {ctx.author.display_name}.", description=f"**Reason:**\n*{reason}*", color=discord.Color.red()))

    @commands.hybrid_command(name='ban')
    @app_commands.describe(
        member='The member to ban.',
        reason='The reason for this ban.'
    )
    @commands.has_permissions(ban_members=True)
    async def ban_command(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = "No reason was provided"):
        """
        Ban a member.

        This command requires you to have ban members permission to execute.
        """
        await member.ban(reason=reason)
        await ctx.send(embed=discord.Embed(title=f"**{member.display_name}** _is banned by_ {ctx.author.display_name}.", description=f"**Reason:**\n*{reason}*", color=discord.Color.red()))

    @commands.hybrid_command(name='unban')
    @app_commands.describe(
        member='The member to unban.',
        reason='The reason for this unban.'
    )
    @commands.has_permissions(ban_members=True)
    async def unban_command(self, ctx: commands.Context, member: discord.User, *, reason: Optional[str] = "No reason was provided"):
        """
        Unban a member.

        This command requires you to have ban members permission to execute.
        """
        async for entry in ctx.guild.bans():
            if entry.user == member:
                await ctx.guild.unban(entry.user, reason=reason)
                return await ctx.send(embed=discord.Embed(title=f"**{member.display_name}** _is unbanned by_ {ctx.author.display_name}.", description=f"**Reason:**\n*{reason}*", color=discord.Color.red()))
        return await ctx.send(embed=discord.Embed(title=f"No member in guild bans matches.", color=discord.Color.red()))

    @commands.hybrid_command(name='spam')
    @app_commands.describe(
        times='The number of messages.',
        msg='The message to spam.'
    )
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def spam_command(self, ctx: commands.Context, times: Optional[int], msg: str):
        """
        Spams a message of yours.

        Spam a message at max 10 times for normal members. 
        Administrator can spam as many as possible.
        """
        if not times:
            times = 1

        if ctx.author.guild_permissions.administrator == True:
            for i in range(times):
                await ctx.send(f'{msg}')
                await asyncio.sleep(0.5)
        else:
            if times > 10:
                return await ctx.send("You don't have permission to spam more than 10 times.")
            else:
                for i in range(times):
                    await ctx.send(f'{msg}')

    @commands.hybrid_command(name='timer')
    @app_commands.describe(
        time='The timer time.'
    )
    async def timer_command(self, ctx, time: str = "5s"):
        """
        Sets a timer.

        Sets a timer according to the given time.
        """
        x = from_time_format_to_seconds(time)
        if not x:
            raise commands.BadArgument(
                r"The time argument doesn't match the format.")
        if x >= 86400:
            raise commands.BadArgument(r"The time argument is too long.")
        t = x
        embed = discord.Embed(
            title='(☞ﾟヮﾟ)☞  ' + from_seconds_to_time_format(x) + '  ☜(ﾟヮﾟ☜)', color=discord.Color.red())
        embed.set_author(name="Timer started.")
        embed.set_footer(icon_url=ctx.author.display_avatar.url,
                         text=f'Requested by {ctx.author}')
        msg = await ctx.send(embed=embed)
        for i in range(t):
            x -= 1
            embed = discord.Embed(
                title='(☞ﾟヮﾟ)☞  ' + from_seconds_to_time_format(x) + '  ☜(ﾟヮﾟ☜)', color=discord.Color.red())
            embed.set_author(name="Timer started.")
            embed.set_footer(icon_url=ctx.author.display_avatar.url,
                             text=f'Requested by {ctx.author}')
            await asyncio.sleep(1)
            await msg.edit(embed=embed)
        if x <= 0:
            embed = discord.Embed(
                title='(☞ﾟヮﾟ)☞  ' + from_seconds_to_time_format(x) + '  ☜(ﾟヮﾟ☜)', color=discord.Color.red())
            embed.set_author(name="Timer ended.")
            embed.set_footer(icon_url=ctx.author.display_avatar.url,
                             text=f'Requested by {ctx.author}')
            await msg.edit(embed=embed)

    @commands.hybrid_command(name='emoji', aliases=['emo'])
    @app_commands.describe(
        times='The number of emojis to send.'
    )
    async def emoji_command(self, ctx, times=1):
        """
        Sends a random emoji.

        Sends a random emoji.
        """
        # response = ''
        # for i in range(times):
        #     response += str(random.choice(ctx.bot.emojis))
        # await ctx.send(f'{response}')
        await ctx.send(len(ctx.bot.emojis))
        for emoji in ctx.bot.emojis:
            await ctx.send(f"{emoji}")

    @commands.hybrid_command(name='randcard', aliases=['card', 'bocbai'])
    async def randcard_command(self, ctx: commands.Context):
        """
        Picks a random card from deck.

        Picks a random card for you.
        Could be used for small giveaway.
        """
        number = ['Aces', 'Two', 'Three', 'Four', 'Five', 'Six',
                  'Seven', 'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King']
        type = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        num = random.choice(number)
        ty = random.choice(type)
        card = "You have picked " + num + " of " + ty + '!'
        filepath = num + ty + '.png'
        file = discord.File('Images//PlayCards//' + filepath)
        embed = discord.Embed(title=card, color=discord.Color.red())
        embed.set_image(url=f'attachment://{filepath}')
        embed.set_footer(icon_url=ctx.author.display_avatar.url,
                         text=f"Requested by {ctx.author.name}")
        await ctx.send(file=file, embed=embed)

    @commands.hybrid_command()
    async def suicide(self, ctx):
        """
        Use this command if you want to suicide

        Don't suicide.
        """
        response = ["Don't be so sad! Life is great! Even for losers like me!",
                    "Be positive! There are people who believe in you!",
                    "You are the best! Be my friend!",
                    "At least you are better than me! And I am a great bot!",
                    "In this world, there will definitely be one who shed tears if you commit suicide."]
        await ctx.send(embed=discord.Embed(description=f'_**{random.choice(response)}**_', color=discord.Color.red()))

    @commands.hybrid_command()
    async def paradox(self, ctx):
        """
        Sends you a paradox.

        Sends a paradox that can break your minds.
        """
        response = list(db.paradox.aggregate(
            [{"$sample": {"size": 1}}]))[0]['content']
        embed = discord.Embed(description='***' + response + '***',
                              color=discord.Color.red())
        embed.title = "( •̀ .̫ •́ )✧Paradox: "
        embed.set_footer(icon_url=ctx.author.display_avatar.url,
                         text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(miscellaneous(bot))
