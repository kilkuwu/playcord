import discord

class Confirm(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.value = False
        self.id = user.id

    @discord.ui.button(label="CONFIRM", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user.id != self.id:
            return
        self.value = True
        self.stop()

    @discord.ui.button(label="CANCEL", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if interaction.user.id != self.id:
            return
        self.value = False
        self.stop()