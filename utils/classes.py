from discord.ext import commands

class BotError(commands.CommandError):
    """
    Error code:
        41: Already connected to voice channel
        42: No voice channel
        43: Queue is empty
        44: No tracks found
        45: Autoplay Error
        46: Invalid playlist
    """

    def __init__(self, message=None, code: int = None, cate: str = None, *args) -> None:
        super().__init__(message, *args)
        self.code = code
        self.cate = cate