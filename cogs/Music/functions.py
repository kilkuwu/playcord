import os
import random
import yt_dlp
import aiohttp
import asyncio
from .constants import YTDLP, YTDL
from utils.functions import format_api_arguments

def include_playlist(flag):
    return YTDLP if flag else YTDL

async def get_autoplay_video(video_id, video_title):
    url = format_api_arguments(
        "https://youtube.googleapis.com/youtube/v3/search?",
        part='snippet',
        type='video',
        relatedToVideoId=video_id,
        maxResults=50,
        fields="nextPageToken,items(snippet(title),id(videoId))",
        key=os.getenv('GAPIKEY')
    )

    async with aiohttp.ClientSession() as session:
        response = await (await session.get(url)).json()

    choose = [x for x in response['items'] if "snippet" in x]

    try_searching = False

    while not choose:
        if not "nextPageToken" in response:
            if not try_searching:
                retry_url = format_api_arguments(
                    "https://youtube.googleapis.com/youtube/v3/search?",
                    part='snippet',
                    type='video',
                    topicId="/m/04rlf",
                    q="LEMMiNO - Infinity",
                    maxResults=50,
                    fields="nextPageToken,items(snippet(title),id(videoId))",
                    key=os.getenv('GAPIKEY')
                )
                async with aiohttp.ClientSession() as session:
                    response = await (await session.get(retry_url)).json()

                choose = [x for x in response['items'] if "snippet" in x]
            else:
                return None
        else:
            if not try_searching:
                retry_url = url + f"nextPageToken={response['nextPageToken']}"
                async with aiohttp.ClientSession() as session:
                    response = await (await session.get(retry_url)).json()

                choose = [x for x in response['items'] if "snippet" in x][:3]
            else:
                retry_url = format_api_arguments(
                    "https://youtube.googleapis.com/youtube/v3/search?",
                    part='snippet',
                    type='video',
                    topicId="/m/04rlf",
                    q=video_title,
                    maxResults=50,
                    fields="nextPageToken,items(snippet(title),id(videoId))",
                    pageToken=response['nextPageToken'],
                    key=os.getenv('GAPIKEY')
                )
                async with aiohttp.ClientSession() as session:
                    response = await (await session.get(retry_url)).json()

                choose = [x for x in response['items'] if "snippet" in x]

    return "https://www.youtube.com/watch?v=" + random.choice(choose)['id']['videoId']


async def get_prime_ytdl_data(loop, ytdl, query):
    try:
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
    except yt_dlp.DownloadError:
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False, force_generic_extractor=True))
        except yt_dlp.DownloadError as e:
            return e
    return data


async def get_ytdl_data(loop, ytdl: yt_dlp.YoutubeDL, query):
    try:
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
    except yt_dlp.DownloadError:
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False, force_generic_extractor=True))
        except yt_dlp.DownloadError as e:
            return [e]
    if "entries" in data:
        data = data['entries']
        urls = ["https://www.youtube.com/watch?v="+item["id"] for item in data]
        return await get_multiple_ytdl_data(loop, ytdl, urls)
    return [dict(
        url=data.get('url', None),
        webpage_url=data.get('webpage_url', None),
        title=data.get('title', None),
        duration=data.get('duration', None)
    )]


async def get_multiple_ytdl_data(loop, ytdl, queries):
    datas = []
    tasks = []
    length = len(queries)
    for i, query in enumerate(queries):
        tasks.append(get_ytdl_data(loop, ytdl, query))
        if (i != 0 and i % 30 == 0) or i == length - 1:
            data = await asyncio.gather(*tasks)
            for item in data:
                datas.extend(item)
            tasks.clear()
    return datas
