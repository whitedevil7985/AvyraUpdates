import asyncio
import re
from typing import Union

import aiohttp
from bs4 import BeautifulSoup
from py_yt import VideosSearch


class RessoAPI:
    def __init__(self):
        self.regex = r"^(https:\/\/m.resso.com\/)(.*)$"
        self.base = "https://m.resso.com/"

    async def valid(self, link: str):
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def track(self, url, playid: Union[bool, str] = None):
        if playid:
            url = self.base + url
        timeout = aiohttp.ClientTimeout(total=10, connect=4, sock_read=7)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return False
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")
        title = None
        description = ""
        for tag in soup.find_all("meta"):
            if tag.get("property") == "og:title":
                title = tag.get("content")
            elif tag.get("property") == "og:description":
                description = tag.get("content") or ""

        if not title:
            raise ValueError("Resso page did not contain a track title")

        # Resso pages only provide metadata; resolve the actual playable YouTube track.
        results = VideosSearch(title, limit=1)
        data = await asyncio.wait_for(results.next(), timeout=12)
        matches = data.get("result") or []
        if not matches:
            raise ValueError("No matching YouTube track found for this Resso link")

        result = matches[0]
        thumbnail_list = result.get("thumbnails") or []
        track_details = {
            "title": result.get("title") or title,
            "link": result["link"],
            "vidid": result["id"],
            "duration_min": result.get("duration"),
            "thumb": thumbnail_list[0]["url"].split("?")[0] if thumbnail_list else "",
        }
        return track_details, result["id"]
