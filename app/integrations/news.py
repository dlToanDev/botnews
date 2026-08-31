"""Adapter Tin tức — RSS chuyên mục VNExpress (feedparser). Mỗi item gắn category + image."""
import re

import feedparser

from app.core.constants import NEWS_CATEGORIES
from app.integrations.base import BaseAdapter, http_get_text

_IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_PER_FEED = 15  # số tin lấy tối đa mỗi chuyên mục


def _extract_image(entry) -> str | None:
    """Tìm URL ảnh banner của 1 entry RSS. None nếu không có."""
    thumb = entry.get("media_thumbnail")
    if thumb and thumb[0].get("url"):
        return thumb[0]["url"]
    media = entry.get("media_content")
    if media and media[0].get("url"):
        return media[0]["url"]
    for coll in (entry.get("enclosures"), entry.get("links")):
        for link in coll or []:
            if str(link.get("type", "")).startswith("image") and link.get("href"):
                return link["href"]
    m = _IMG_RE.search(entry.get("summary") or entry.get("description") or "")
    return m.group(1) if m else None


def _parse_feed(text: str, category: str) -> list[dict]:
    """Parse XML 1 feed → list item, gắn category cho từng tin."""
    parsed = feedparser.parse(text)
    items = []
    for e in parsed.entries[:_PER_FEED]:
        items.append(
            {
                "title": e.get("title", "").strip(),
                "link": e.get("link", ""),
                "published": e.get("published", ""),
                "source": "vnexpress",
                "category": category,
                "image": _extract_image(e),
            }
        )
    return items


class NewsAdapter(BaseAdapter):
    """Trả list item: {title, link, published, source, category, image}."""

    name = "news:rss"
    ttl = 120  # 2 phút (khớp nhịp đẩy tin)

    async def fetch(self):
        items = []
        for cat in NEWS_CATEGORIES:
            try:
                text = await http_get_text(cat["rss"], timeout=8.0)
            except Exception:  # noqa: BLE001
                continue
            items.extend(_parse_feed(text, cat["key"]))
        return items


news_adapter = NewsAdapter()


async def get_news() -> list[dict]:
    return await news_adapter.get()


def match_keywords(title: str, keywords: list[str]) -> bool:
    if not keywords:
        return False
    low = title.lower()
    return any(kw.lower() in low for kw in keywords)
