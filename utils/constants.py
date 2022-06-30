import os
import discord
from pymongo import MongoClient

DB = MongoClient(os.getenv('MONGODBURL')).discord

GUILDS_DB = DB.guilds
PARADOX_DB = DB.paradox
USERS_DB = DB.users

GUILDS = [
    discord.Object(id=867362365536337950),
    discord.Object(id=869232232819200061)
]

TIME_REGEX = r"^(?:(\d{1,6})s?)$|^(\d{1,4})[:m](?:(\d{1,6})s?)?$|^(\d{1,2})[:h](?:(\d{1,4})[:m])?(?:(\d{1,6})s?)?$"
