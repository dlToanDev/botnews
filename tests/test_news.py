"""Unit test tin tức đa chuyên mục + trích ảnh + lọc đẩy (thuần, không gọi mạng)."""
from app.bot.handlers.features import _news_caption, _pick_news
from app.integrations.news import _extract_image, _parse_feed
from app.worker.tasks.news_push import _passes_filter


# ---------------- Trích ảnh banner ----------------

def test_extract_image_from_media_thumbnail():
    entry = {"media_thumbnail": [{"url": "https://img/a.jpg"}]}
    assert _extract_image(entry) == "https://img/a.jpg"


def test_extract_image_from_enclosure():
    entry = {"links": [{"rel": "enclosure", "type": "image/jpeg", "href": "https://img/b.jpg"}]}
    assert _extract_image(entry) == "https://img/b.jpg"


def test_extract_image_from_summary_img_tag():
    entry = {"summary": '<a href="x"><img src="https://img/c.jpg"/></a> tóm tắt'}
    assert _extract_image(entry) == "https://img/c.jpg"


def test_extract_image_none_when_absent():
    assert _extract_image({"summary": "chỉ có chữ, không ảnh"}) is None


# ---------------- Parse feed gắn category ----------------

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title><![CDATA[Tin thể thao số 1]]></title>
  <link>https://vnexpress.net/bai-1.html</link>
  <description><![CDATA[<img src="https://img/1.jpg"/> tóm tắt 1]]></description>
  <pubDate>Fri, 28 Aug 2026 10:00:00 +0700</pubDate>
</item>
<item>
  <title><![CDATA[Tin thể thao số 2]]></title>
  <link>https://vnexpress.net/bai-2.html</link>
  <description><![CDATA[không ảnh]]></description>
  <pubDate>Fri, 28 Aug 2026 09:00:00 +0700</pubDate>
</item>
</channel></rss>"""


def test_parse_feed_tags_category_and_fields():
    items = _parse_feed(_SAMPLE_RSS, "thethao")
    assert len(items) == 2
    first = items[0]
    assert first["title"] == "Tin thể thao số 1"
    assert first["link"] == "https://vnexpress.net/bai-1.html"
    assert first["category"] == "thethao"
    assert first["image"] == "https://img/1.jpg"
    assert items[1]["image"] is None


# ---------------- Lọc đẩy cho từng user ----------------

_ITEM = {"title": "Arsenal thắng đậm", "link": "l", "category": "thethao", "image": None}


def test_passes_filter_empty_cats_accepts_all():
    assert _passes_filter(_ITEM, [], []) is True


def test_passes_filter_matching_category():
    assert _passes_filter(_ITEM, ["thethao", "thoisu"], []) is True


def test_passes_filter_non_matching_category():
    assert _passes_filter(_ITEM, ["kinhdoanh"], []) is False


def test_passes_filter_keyword_narrows_within_category():
    assert _passes_filter(_ITEM, ["thethao"], ["arsenal"]) is True
    assert _passes_filter(_ITEM, ["thethao"], ["chelsea"]) is False


# ---------------- Lệnh /news: chọn tin + caption ----------------

_ITEMS = [
    {"title": "TT1", "link": "l1", "category": "thethao", "image": "i1"},
    {"title": "KD1", "link": "l2", "category": "kinhdoanh", "image": "i2"},
    {"title": "TT2 không ảnh", "link": "l3", "category": "thethao", "image": None},
    {"title": "TT3", "link": "l4", "category": "thethao", "image": "i4"},
]


def test_pick_news_all_categories_only_with_image():
    picked = _pick_news(_ITEMS, None, 10)
    assert [p["link"] for p in picked] == ["l1", "l2", "l4"]  # l3 bị loại vì không ảnh


def test_pick_news_filters_by_category():
    picked = _pick_news(_ITEMS, "thethao", 10)
    assert [p["link"] for p in picked] == ["l1", "l4"]


def test_pick_news_respects_limit():
    assert len(_pick_news(_ITEMS, None, 2)) == 2


def test_news_caption_has_title_and_link():
    cap = _news_caption({"title": "Tin nóng", "link": "https://x/y", "image": "i"})
    assert "Tin nóng" in cap
    assert "https://x/y" in cap


# ---------------- effective_news_cats (user override / mặc định hệ thống) ----------------
from app.worker.tasks.news_push import effective_news_cats  # noqa: E402


def test_effective_news_prefers_user():
    assert effective_news_cats(["thethao"], ["thoisu"]) == ["thethao"]


def test_effective_news_falls_back_to_default():
    assert effective_news_cats([], ["thoisu", "thegioi"]) == ["thoisu", "thegioi"]


def test_effective_news_empty_both():
    assert effective_news_cats([], []) == []
