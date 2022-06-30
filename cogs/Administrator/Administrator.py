import discord
from discord.ext import commands
from cogs.Battle.classes.Inventory.item import get_default_item_by_name, get_item
from cogs.Battle.classes.User import User
from utils.functions import get_default_embed, verify_and_get_user
from utils.constants import GUILDS, USERS_DB

class administrator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='give')
    @commands.is_owner()
    async def give_command(self, ctx, member: discord.Member, count: int, *, item
    : str):
        user, message = await verify_and_get_user(ctx, member.id)

        if not user:
            return await message.edit(embed=get_default_embed(ctx, f"Your target might not have an Eyes of Heaven profile."))

        user.inventory.add_by_name(user.inventory.items, item, count)            
        user.update_inventory()
        await message.edit(embed=get_default_embed(ctx, 'SUCCESSFUL COMMAND', f"***Added {count} x {item} to {member.mention}'s inventory***"))
    
    @commands.hybrid_command(name='takeaway')
    @commands.is_owner()
    async def takeaway_command(self, ctx, member: discord.Member, count: int, *, item: str):
        user, message = await verify_and_get_user(ctx, member.id)

        if not user:
            return await message.edit(embed=get_default_embed(ctx, f"Your target might not have an Eyes of Heaven profile."))

        existed, count = user.inventory.remove_by_name(user.inventory.items, item, count)
        user.update_inventory()
        await message.edit(embed=get_default_embed(ctx, 'SUCCESSFUL COMMAND', f"***Removed {count} x {item} to {member.mention}'s inventory***"))
    
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