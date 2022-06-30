import discord

class Pagelist(discord.ui.View):
    def __init__(self, pagelist, timeout = 180, page_number: int = 0):
        super().__init__(timeout=timeout)
        self.value = None
        self.pagelist = pagelist
        self.current_page = page_number
        self.maxpage = len(pagelist) - 1

    @discord.ui.button(style=4, emoji="⏮")
    async def firstpage(self, interaction: discord.Interaction, button: discord.ui.Button, ):
        self.current_page = 0
        await interaction.response.edit_message(embed=self.pagelist[self.current_page])

    @discord.ui.button(style=2, emoji="◀")
    async def previouspage(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page == 0:
            await interaction.response.edit_message(embed=self.pagelist[self.current_page])
        else:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.pagelist[self.current_page])

    @discord.ui.button(style=2, emoji="▶")
    async def nextpage(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page == self.maxpage:
            await interaction.response.edit_message(embed=self.pagelist[self.current_page])
        else:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.pagelist[self.current_page])

    @discord.ui.button(style=4, emoji="⏭")
    async def lastpage(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.maxpage
        await interaction.response.edit_message(embed=self.pagelist[self.current_page])
