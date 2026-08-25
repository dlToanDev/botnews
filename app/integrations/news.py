"""Adapter Tin tức — RSS (feedparser), không cần key."""
import feedparser

from app.integrations.base import BaseAdapter, http_get_text

# Có thể mở rộng thêm nguồn
RSS_FEEDS = {
    "vnexpress": "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "tuoitre": "https://tuoitre.vn/rss/tin-moi-nhat.rss",
}


class NewsAdapter(BaseAdapter):
    """Trả list item: {title, link, published, source}."""

    name = "news:rss"
    ttl = 600  # 10 phút

    async def fetch(self):
        items = []
        for source, url in RSS_FEEDS.items():
            try:
                text = await http_get_text(url, timeout=8.0)
            except Exception:  # noqa: BLE001
                continue
            parsed = feedparser.parse(text)
            for e in parsed.entries[:20]:
                items.append(
                    {
                        "title": e.get("title", "").strip(),
                        "link": e.get("link", ""),
                        "published": e.get("published", ""),
                        "source": source,
                    }
                )
        return items


news_adapter = NewsAdapter()


async def get_news() -> list[dict]:
    return await news_adapter.get()


def match_keywords(title: str, keywords: list[str]) -> bool:
    if not keywords:
        return False
    low = title.lower()
    return any(kw.lower() in low for kw in keywords)
