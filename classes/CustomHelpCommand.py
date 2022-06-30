import discord
from discord.ext import commands
from views import Pagelist
from utils.functions import get_default_embed


class CustomPaginator:
    def __init__(self, max_size=2000):
        self.max_size = max_size
        self.clear()

    def clear(self):
        """Clears the paginator to have no pages."""
        self._current_page = ""
        self._count = 0
        self._pages = []

    def add_line(self, line='', *, getdown=True, empty=True):
        """Adds a line to the current page.

        If the line exceeds the :attr:`max_size` then an exception
        is raised.

        Parameters
        -----------
        line: :class:`str`
            The line to add.
        empty: :class:`bool`
            Indicates if another empty line should be added.

        Raises
        ------
        RuntimeError
            The line was too big for the current :attr:`max_size`.
        """
        max_page_size = self.max_size - 2
        if len(line) > max_page_size:
            raise RuntimeError(
                f'Line exceeds maximum page size {max_page_size}')

        if self._count + len(line) + 1 > self.max_size - 1:
            self.close_page()

        self._count += len(line)
        self._current_page += line

        if getdown:
            self._current_page += '\n'
            self._count += 1

    def close_page(self):
        """Prematurely terminate a page."""
        self._pages.append(self._current_page)
        self._current_page = ""
        self._count = 0

    def __len__(self):
        total = sum(len(p) for p in self._pages)
        return total + self._count

    @property
    def page_count(self):
        return len(self._pages)

    @property
    def pages(self):
        """List[:class:`str`]: Returns the rendered list of pages."""
        # we have more than just the prefix in our current page
        if len(self._current_page) > 0:
            self.close_page()
        return self._pages

    def __repr__(self):
        fmt = '<Paginator pages: {0.page_count} max_size: {0.max_size} count: {0._count}>'
        return fmt.format(self)


class CustomHelpCommand(commands.DefaultHelpCommand):
    def __init__(self, show_empty=False):
        super().__init__(no_category="Helper", paginator=CustomPaginator(),
                         width=66, indent=1, commands_heading="**Subcommands:**")
        self.show_empty = show_empty
        self._show_hidden = self.show_hidden

    async def send_pages(self):
        embedlist = []
        length = len(self.paginator.pages)
        for i, page in enumerate(self.paginator.pages):
            emby = discord.Embed(
                title="**HELP SECTION:**", description=page, color=discord.Colour.dark_red())
            emby.set_author(
                name=f"Page {i+1}/{length}", icon_url=self.context.bot.user.display_avatar.url)
            emby.set_footer(text="Requested by {}".format(
                self.context.author), icon_url=self.context.author.avatar.url)
            embedlist.append(emby)
        if len(embedlist) <= 1:
            return await self.context.reply(embed=embedlist[0], mention_author=False)
        view = Pagelist(embedlist, timeout=60.0)
        message = await self.context.reply(embed=embedlist[0], view=view, mention_author=False)
        timeout = await view.wait()
        if timeout:
            return await message.edit(view=None)

    def get_bot_mapping(self):
        bot = self.context.bot
        mapping = {}
        for cogname, cog in bot.cogs.items():
            commands = cog.get_commands()
            mapping[cogname] = commands if self.show_hidden else filter(
                lambda c: not c.hidden, commands)
            mapping[cogname] = list(mapping[cogname])
        mapping[self.no_category] = [c for c in bot.commands if c.cog is None]
        return mapping

    async def send_error_message(self, error):
        ctx = self.context
        embed = get_default_embed(
            ctx=ctx,
        ).set_author(
            name=f"Failure executing {ctx.command if ctx.command else ''} command:",
            icon_url=ctx.bot.user.display_avatar.url
        )

        message = str(error).replace("[0;31m", "").replace("[0m", "")

        if len(message) <= 256:
            embed.title = message
        else:
            embed.description = f"**{message}**"

        return await ctx.reply(embed=embed, mention_author=False)

    async def send_bot_help(self, mapping: dict):
        for category, commandlist in mapping.items():
            commandlist = sorted(
                commandlist, key=lambda c: c.name) if self.sort_commands else commandlist
            if not commandlist and not self.show_empty:
                continue
            self.add_indented_commands(commandlist, heading=self.upbold(
                category + ":"))
            self.paginator.close_page()
        await self.send_pages()

    def add_indented_commands(self, commands, *, heading, max_size=None):
        self.paginator.add_line(heading)
        if not commands:
            self.paginator.add_line(self.shorten_text("None"))
            return
        max_size = max_size or self.get_max_size(commands)

        get_width = discord.utils._string_width
        entry = ''
        for command in commands:
            name = command.name
            width = max_size - get_width(name) + len(name)
            entry += f'```{name:<{width}} | {command.short_doc}```'
        self.paginator.add_line(entry)

    def uppitalibold(self, text: str):
        return f"***{text.upper()}***"

    def upbold(self, text: str):
        return f"**{text.upper()}**"

    def shorten_text(self, text, deprecate=0):
        """:class:`str`: Shortens text to fit into the :attr:`width`."""
        length = len(text)
        if length > self.width:
            return '`' + text[:self.width - 2].rstrip() + '...' + '`'
        return '`' + text + f"{(self.width-length-deprecate)*' '}" + '`'

    async def send_cog_help(self, cog: commands.Cog):
        if cog.description:
            self.paginator.add_line(cog.description)
            self.paginator.add_line()
        commands = cog.get_commands()
        filtered = sorted(
            commands, key=lambda c: c.name) if self.sort_commands else commands
        self.add_indented_commands(
            filtered, heading=self.upbold(cog.__cog_name__ + ":"))

        await self.send_pages()

    async def send_command_help(self, command):
        self.add_command_formatting(command)
        self.paginator.close_page()
        await self.send_pages()

    def add_command_formatting(self, command: commands.HybridGroup):
        """A utility function to format the non-indented block of commands and groups.

        Parameters
        ------------
        command: :class:`Command`
            The command to format.
        """
        signature, parent_sig = self.get_command_signature(command)
        self.paginator.add_line("**Formula: **")
        self.paginator.add_line("```" + signature + "```", getdown=False)

        if command.app_command:
            if isinstance(command, commands.HybridGroup):
                pass
            else:
                self.paginator.add_line("**Parameters: **")
                self.paginator.add_line("```")
                get_width = discord.utils._string_width
                max_size = max([get_width(name)
                            for name in command.app_command._params], default=0)
                for name, param in command.app_command._params.items():
                    symbol = '<>' if param.required else '[]'
                    description = getattr(param, 'description', '...')
                    cname = symbol[0] + name + symbol[1]
                    width = max_size - get_width(cname) + len(cname) + 2
                    self.paginator.add_line(
                        line=f"{cname:<{width}} | {description}"
                    )
                self.paginator.add_line("```", getdown=False)

        if len(command.aliases) > 0:
            self.paginator.add_line("**Aliases: **")
            self.paginator.add_line("```" + (parent_sig + " " if parent_sig else "") +
                                    "|".join(command.aliases) + "```", getdown=False)

        if command.help:
            self.paginator.add_line("**Description: **")
            self.paginator.add_line("```")
            try:
                self.paginator.add_line(command.help)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
            self.paginator.add_line("```", getdown=False)
        

    def get_command_signature(self, command):
        """Retrieves the signature portion of the help page.

        Parameters
        ------------
        command: :class:`Command`
            The command to get the signature of.

        Returns
        --------
        :class:`str`
            The signature for the command.
        """

        parent = command.parent
        entries = []
        while parent is not None:
            if not parent.signature or parent.invoke_without_command:
                entries.append(parent.name)
            else:
                entries.append(parent.name + ' ' + parent.signature)
            parent = parent.parent
        parent_sig = ' '.join(reversed(entries))

        alias = command.name if not parent_sig else parent_sig + ' ' + command.name

        return f'{self.context.clean_prefix}{alias} {command.signature}', parent_sig

    async def send_group_help(self, group):
        self.add_command_formatting(group)

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        self.add_indented_commands(filtered, heading=self.commands_heading)

        await self.send_pages()

    async def command_callback(self, ctx, /, *, command=None) -> None:
        command = command.lower() if command else None
        self.show_hidden |= await ctx.bot.is_owner(ctx.author)
        await super().command_callback(ctx, command=command)
        self.show_hidden = self._show_hidden
