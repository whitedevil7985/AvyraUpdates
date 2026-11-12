import asyncio
import json
import re
from html import unescape
from typing import Union
from urllib.parse import unquote, urlparse

import aiohttp
from bs4 import BeautifulSoup
from py_yt import VideosSearch


class RessoAPI:
    def __init__(self):
        self.regex = r"^https?://(?:m\.)?resso\.com/.*$"
        self.base = "https://m.resso.com/"

    async def valid(self, link: str):
        return bool(re.match(self.regex, str(link or ""), re.IGNORECASE))

    @staticmethod
    def _extract_title(html: str):
        soup = BeautifulSoup(html, "html.parser")

        # Resso has changed its page metadata formats over time. Check the
        # common OpenGraph/Twitter tags, JSON-LD, and finally the page title.
        for key, value in (
            ("property", "og:title"),
            ("name", "twitter:title"),
            ("itemprop", "name"),
        ):
            tag = soup.find("meta", attrs={key: value})
            if tag and tag.get("content"):
                title = unescape(tag["content"]).strip()
                if title:
                    return title

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                payload = json.loads(script.string or script.get_text())
                objects = payload if isinstance(payload, list) else [payload]
                for item in objects:
                    if isinstance(item, dict):
                        title = item.get("name") or item.get("headline")
                        if title and str(title).strip():
                            return unescape(str(title)).strip()
            except (TypeError, ValueError):
                continue

        if soup.title and soup.title.string:
            title = unescape(soup.title.string).strip()
            if title and title.lower() not in {"resso", "resso - music"}:
                return title
        return None

    async def track(self, url, playid: Union[bool, str] = None):
        if playid:
            url = self.base + str(url).lstrip("/")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13; Mobile) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Mobile Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        timeout = aiohttp.ClientTimeout(total=9, connect=3, sock_read=5)
        html = ""
        page_url = url
        async with aiohttp.ClientSession(
            timeout=timeout, headers=headers, raise_for_status=False
        ) as session:
            async with session.get(url, allow_redirects=True) as response:
                page_url = str(response.url)
                if response.status == 200:
                    html = await response.text(errors="ignore")
                else:
                    raise ValueError(f"Resso returned HTTP {response.status}")

        title = self._extract_title(html) if html else None

        # Some share pages expose the track name only in their redirected URL.
        if not title:
            slug = unquote(urlparse(page_url).path.rsplit("/", 1)[-1])
            slug = re.sub(r"[-_]+", " ", slug)
            slug = re.sub(r"\\b(?:track|song|share)\\b", " ", slug, flags=re.I)
            slug = re.sub(r"\\s+", " ", slug).strip(" -_")
            if len(slug) >= 4 and not re.fullmatch(r"[0-9a-f-]{8,}", slug, re.I):
                title = slug

        if not title:
            raise ValueError("Resso did not provide track metadata")

        # Resso pages contain metadata, not a reliable playable audio stream.
        # Resolve the title to YouTube and let the normal audio resolver handle it.
        search_query = title
        results = VideosSearch(search_query, limit=3)
        data = await asyncio.wait_for(results.next(), timeout=8)
        matches = data.get("result") or []
        if not matches:
            raise ValueError(f"No playable match found for Resso track: {title}")

        result = matches[0]
        thumbnails = result.get("thumbnails") or []
        thumbnail = ""
        if thumbnails:
            first = thumbnails[0]
            thumbnail = first.get("url", "") if isinstance(first, dict) else str(first)
            thumbnail = thumbnail.split("?")[0]

        track_details = {
            "title": result.get("title") or title,
            "link": result["link"],
            "vidid": result["id"],
            "duration_min": result.get("duration"),
            "thumb": thumbnail,
        }
        return track_details, result["id"]
