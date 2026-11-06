import os
import asyncio
from types import SimpleNamespace

import aiohttp
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import YOUTUBE_IMG_URL

try:
    from unidecode import unidecode
except ImportError:
    def unidecode(text):
        return text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "..", "assets")
FONT_TITLE_PATH = os.path.join(ASSETS_DIR, "font.ttf")
FONT_INFO_PATH = os.path.join(ASSETS_DIR, "font2.ttf")
TEMPLATE_PATH = os.path.join(ASSETS_DIR, "template.jpg")

W, H = 1280, 720


def safe_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


class Thumbnail:
    def __init__(self):
        self.size = (W, H)
        self.font_title = safe_font(FONT_TITLE_PATH, 26)
        self.font_info = safe_font(FONT_INFO_PATH, 20)

    async def save_thumb(self, output_path: str, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        for attempt in range(3):
            try:
                if url.startswith("http"):
                    async with aiohttp.ClientSession(headers=headers) as session:
                        async with session.get(url, timeout=15) as resp:
                            if resp.status == 200:
                                content = await resp.read()
                                with open(output_path, "wb") as f:
                                    f.write(content)
                                return output_path
            except Exception as e:
                if attempt == 2:
                    print(f"Error saving thumb: {e}")
                await asyncio.sleep(1)
        return output_path

    async def generate(self, song) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            temp = f"cache/temp_{song.id}.jpg"
            final_path = f"cache/{song.id}.png"
            if os.path.exists(final_path):
                return final_path

            await self.save_thumb(temp, song.thumbnail)

            try:
                src = Image.open(temp).convert("RGBA")
            except Exception:
                src = Image.new("RGBA", (W, H), (30, 30, 30, 255))

            # 1. Blurred background from the song image
            bg_ratio = W / H
            src_ratio = src.width / src.height
            if src_ratio > bg_ratio:
                new_w = int(src.height * bg_ratio)
                offset = (src.width - new_w) // 2
                bg = src.crop((offset, 0, offset + new_w, src.height))
            else:
                new_h = int(src.width / bg_ratio)
                offset = (src.height - new_h) // 2
                bg = src.crop((0, offset, src.width, offset + new_h))

            bg = bg.resize((W, H), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(25))

            bg_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 100))
            bg = Image.alpha_composite(bg, bg_overlay)

            # 2. Template with extracted UI (soft alpha)
            if os.path.exists(TEMPLATE_PATH):
                tpl = Image.open(TEMPLATE_PATH).convert("RGBA")
                tpl = tpl.resize((W, H), Image.Resampling.LANCZOS)

                tpl_arr = np.array(tpl).astype(float)
                r, g, b = tpl_arr[:, :, 0], tpl_arr[:, :, 1], tpl_arr[:, :, 2]

                d_bg = np.maximum(np.maximum(np.abs(r - 147.5), np.abs(g - 147.5)), np.abs(b - 147.5))
                alpha = np.clip((d_bg - 8) / 17.0 * 255, 0, 255)
                alpha[:, :640] = 0

                tpl_arr[:, :, 3] = alpha
                tpl = Image.fromarray(tpl_arr.astype(np.uint8))

                bg = Image.alpha_composite(bg, tpl)

            # 3. Cover art with drop shadow
            cover_x, cover_y = 100, 104
            cover_w, cover_h = 512, 512
            cover_radius = 38

            shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_layer)
            shadow_draw.rounded_rectangle(
                (cover_x + 6, cover_y + 8, cover_x + cover_w + 6, cover_y + cover_h + 8),
                radius=cover_radius + 4,
                fill=(0, 0, 0, 140),
            )
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(18))
            bg = Image.alpha_composite(bg, shadow_layer)

            cover_resized = src.resize((cover_w, cover_h), Image.Resampling.LANCZOS)
            cover_mask = Image.new("L", (cover_w, cover_h), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, cover_w, cover_h), radius=cover_radius, fill=255
            )
            bg.paste(cover_resized, (cover_x, cover_y), cover_mask)

            # 4. Text
            draw = ImageDraw.Draw(bg)
            text_x = 715
            text_max_w = 320

            def ellipsize(s, font, max_w):
                if draw.textbbox((0, 0), s, font=font)[2] <= max_w:
                    return s
                lo, hi = 1, len(s)
                best = "…"
                while lo <= hi:
                    mid = (lo + hi) // 2
                    cand = s[:mid].rstrip() + "…"
                    if draw.textbbox((0, 0), cand, font=font)[2] <= max_w:
                        best = cand
                        lo = mid + 1
                    else:
                        hi = mid - 1
                return best

            title_str = ellipsize(unidecode(str(song.title)), self.font_title, text_max_w)
            title_y = cover_y + 12
            draw.text((text_x, title_y), title_str, fill=(255, 255, 255, 255), font=self.font_title)

            artist_str = ellipsize(unidecode(str(song.channel_name)), self.font_info, text_max_w + 60)
            artist_y = title_y + 40
            draw.text((text_x, artist_y), artist_str, fill=(200, 200, 200, 255), font=self.font_info)

            out = bg.convert("RGB")
            out.save(final_path, "PNG")

            try:
                if os.path.exists(temp):
                    os.remove(temp)
            except Exception:
                pass

            return final_path

        except Exception as e:
            print(f"Thumbnail error: {e}")
            return YOUTUBE_IMG_URL


_thumbnail = Thumbnail()


async def get_thumb(videoid):
    final_path = f"cache/{videoid}.png"
    if os.path.isfile(final_path) and os.path.getsize(final_path) > 0:
        return final_path

    try:
        from KanhaMusic.platforms.Youtube import get_video_info

        info = await get_video_info(videoid, mode="audio")
        if not info or not info[0] or info[0] == "N/A":
            return YOUTUBE_IMG_URL
        title = info[0]
        channel = info[4] if info[4] and info[4] != "N/A" else ""
        thumb = info[7]
    except Exception:
        return YOUTUBE_IMG_URL

    if not isinstance(thumb, str) or not thumb.startswith("http"):
        thumb = f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg"

    song = SimpleNamespace(id=videoid, title=title, channel_name=channel, thumbnail=thumb)
    return await _thumbnail.generate(song)
