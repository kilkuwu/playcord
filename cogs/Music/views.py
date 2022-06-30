import discord


class TrackChoosingView(discord.ui.View):
    class TrackChoosingButton(discord.ui.Button):
        def __init__(self, emoji, value):
            super().__init__(emoji=emoji)
            self.value = value

        async def callback(self, interaction: discord.Interaction):
            view: TrackChoosingView = self.view
            view.value = self.value
            await interaction.response.defer()
            view.stop()

    def __init__(self, length, *, timeout=180.0):
        super().__init__(timeout=timeout)
        self.value = None
        EMOJIS_CHOICES = {"1️⃣": 0, "2⃣": 1, "3⃣": 2, "4⃣": 3, "5⃣": 4}
        for emoji in list(EMOJIS_CHOICES.keys())[:min(length, 5)]:
            self.add_item(self.TrackChoosingButton(
                emoji=emoji, value=EMOJIS_CHOICES[emoji]))
