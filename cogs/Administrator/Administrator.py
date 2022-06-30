import discord
from discord.ext import commands
from utils.functions import get_default_embed
from utils.constants import GUILDS

class administrator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='sync', hidden=True)
    @commands.is_owner()
    async def sync_command(self, ctx):
        for guild in GUILDS:
            await self.bot.tree.sync(guild=guild)
        await ctx.reply(embed=get_default_embed(ctx, 'Synced app commands.'), mention_author=False)

    @commands.command(name="toggle", aliases=['tog'], hidden=True)
    @commands.is_owner()
    async def toggle_command(self, ctx, *, command):
        command = self.bot.get_command(command)
        if command is None:
            raise commands.CommandNotFound(
                "The bot doesn't have a command of that name.")
        elif ctx.command == command:
            raise commands.BadArgument("Toggle command cannot be disabled.")
        else:
            command.enabled = not command.enabled
            ternary = "enabled" if command.enabled else "disabled"
            embed = get_default_embed(
                ctx=ctx,
                title=f"{command.qualified_name} is now {ternary}."
            ).set_author(name="Command toggled successfully")
            await ctx.reply(embed=embed, mention_author=False)

async def setup(bot):
    await bot.add_cog(administrator(bot))