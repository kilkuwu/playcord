import asyncio
import discord
from discord.ext import commands
from .CustomHelpCommand import CustomHelpCommand
from utils.constants import GUILDS
from utils.functions import get_default_embed
from utils.classes import BotError

class Bot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(
            command_prefix=commands.when_mentioned_or(command_prefix),
            help_command=CustomHelpCommand(),
            description="A multi purpose bot that serves you well.",
            **options
        )
        self.cmd_pre = command_prefix
    
    async def setup_hook(self) -> None:
        tasks = [
            self.load_extension('cogs.Administrator.Administrator'),
            self.load_extension('cogs.Battle.Battle'),
            self.load_extension('cogs.Helper.Helper'),
            self.load_extension('cogs.Miscellaneous.Miscellaneous'),
            self.load_extension('cogs.Music.Music'),
            self.load_extension('cogs.NSFW.NSFW'),
        ]
        await asyncio.gather(*tasks)
        self.help_command.cog = self.get_cog('helper')
        for guild in GUILDS:
            self.tree.copy_global_to(guild=guild)

    async def on_ready(self):
        print(f"Logged in as {self.user}.")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{self.cmd_pre}help"
            )
        )

    async def on_connect(self):
        print(f"{self.user} has connected.")

    async def on_disconnect(self):
        print(f"{self.user} has disconnected.")

    async def on_command_error(self, ctx: commands.Context, error):
        if hasattr(ctx.command, 'on_error'):
            return

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound)

        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        samething = (
            commands.DisabledCommand,
            commands.MissingRequiredArgument,
            commands.MissingPermissions,
            commands.CommandOnCooldown,
            commands.NotOwner,
            commands.MemberNotFound,
            commands.BadArgument,
            commands.NSFWChannelRequired,
            commands.BadLiteralArgument,
            BotError
        )

        embed = get_default_embed(
            ctx=ctx,
        ).set_author(
            name=f"Failure executing {ctx.command if ctx.command else ''} command:",
            icon_url=self.user.display_avatar.url
        )

        message = str(error).replace("[0;31m", "").replace("[0m", "")

        if len(message) <= 256:
            embed.title = message
        else:
            embed.description = f"**{message}**"

        if isinstance(error, samething):
            pass
        elif isinstance(error, discord.HTTPException):
            if error.code == 50013:
                embed.add_field(
                    name="**Details:**", value=f"The bot doesn't have the required permissions to perform this command", inline=False)
        else:
            await super().on_command_error(ctx, error)

        return await ctx.reply(embed=embed, mention_author=False)