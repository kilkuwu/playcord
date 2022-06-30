import discord

class CalculableAudio(discord.PCMVolumeTransformer):
    def __init__(self, original, start, volume: float):
        self.played = start
        super().__init__(original, volume=volume)

    def read(self) -> bytes:
        self.played += 20
        return super().read()
    
class Track(object):
    def __init__(
        self,
        source=None,
        url=None,
        title=None,
        duration=None,
        requester_id=None
    ):
        self.source = source
        self.url = url
        self.title = title
        self.duration = duration
        self.requester_id = requester_id
    
    @classmethod
    def from_data(cls, ctx, data):
        return cls(
            data['url'],
            data['webpage_url'],
            data['title'],
            data['duration'],
            ctx.author.id
        )