from enum import Enum
import yt_dlp

class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2

class PlayerSettings(object):
    def __init__(self):
        self.multiquery = True
        self.inplaylist = False
        self.autoplay = False

YTDL5 = yt_dlp.YoutubeDL(
    {
        "format": "bestaudio/best",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extract_flat": "in_playlist",
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch5",
        "source_address": "0.0.0.0"
    }
)

YTDL = yt_dlp.YoutubeDL(
    {
        "format": "bestaudio/best",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extract_flat": "in_playlist",
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0"
    }
)
YTDLP = yt_dlp.YoutubeDL(
    {
        "format": "bestaudio/best",
        "restrictfilenames": True,
        "nocheckcertificate": True,
        "extract_flat": "in_playlist",
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0"
    }
)

URL_REGEX = "^(?:(?:(?:https?|ftp):)?\/\/)(?:\S+(?::\S*)?@)?(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z0-9\u00a1-\uffff][a-z0-9\u00a1-\uffff_-]{0,62})?[a-z0-9\u00a1-\uffff]\.)+(?:[a-z\u00a1-\uffff]{2,}\.?))(?::\d{2,5})?(?:[/?#]\S*)?$"
PLAY_MESSAGE_REGEX = r"(^[^ ]* *([1-5]))|(^[^ ]* *e(xit)?$)"
