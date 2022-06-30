import discord
import os
from classes import Bot

def main():
    bot = Bot(
        command_prefix=os.getenv('CMD_PREFIX'),
        intents=discord.Intents(36751),
        owner_id=507429831236124692,
        case_insensitive=True,
    )
    bot.run(os.getenv('BOT_TOKEN'))


if __name__ == '__main__':
    main()
