"""Business logic cho trợ lý AI: quota theo ngày, chat & phân tích theo dịch vụ."""
from app.core.constants import AI_DAILY_LIMIT
from app.core.redis_client import redis_client
from app.core.timeutils import now_local
from app.integrations import crypto, gold, news
from app.integrations.gemini import ask

AI_SYSTEM_PROMPT = (
    "Bạn là trợ lý AI của BotNews — một bot Telegram tại Việt Nam. "
    "Trả lời bằng tiếng Việt, ngắn gọn, rõ ràng, lịch sự. "
    "Nếu không chắc chắn, hãy nói thẳng thay vì bịa. "
    "Định dạng hợp cho Telegram (không dùng bảng phức tạp)."
)

# Dùng cho phân tích tài chính (vàng/crypto): luôn kèm nhắc 'chỉ tham khảo'.
ANALYST_SYSTEM_PROMPT = (
    "Bạn là chuyên viên phân tích thị trường của BotNews. Trả lời tiếng Việt, súc tích. "
    "Chỉ dựa trên số liệu được cung cấp, KHÔNG bịa số. "
    "Kết thúc bằng câu nhắc: đây là thông tin tham khảo, không phải lời khuyên đầu tư."
)

_QUOTA_TTL = 26 * 3600  # ~1 ngày


class NoDataError(Exception):
    """Không lấy được dữ liệu nguồn để phân tích."""


def _quota_key(user_id: int) -> str:
    return f"ai:quota:{user_id}:{now_local().strftime('%Y%m%d')}"


async def check_and_incr(user_id: int, limit: int = AI_DAILY_LIMIT) -> tuple[bool, int]:
    """Kiểm tra + tăng bộ đếm ngày. (được_phép, số_đã_dùng). Không tăng nếu đã đạt hạn."""
    key = _quota_key(user_id)
    used = int(await redis_client.get(key) or 0)
    if used >= limit:
        return False, used
    new_used = await redis_client.incr(key)
    if new_used == 1:
        await redis_client.expire(key, _QUOTA_TTL)
    return True, new_used


async def refund(user_id: int) -> None:
    """Hoàn 1 lượt (khi gọi AI thất bại)."""
    key = _quota_key(user_id)
    if int(await redis_client.get(key) or 0) > 0:
        await redis_client.decr(key)


async def complete(user_id: int, prompt: str, system: str) -> str:
    """Gọi Gemini; hoàn lượt nếu lỗi (quota đã trừ ở handler trước khi gọi)."""
    try:
        return await ask(prompt, system=system)
    except Exception:
        await refund(user_id)
        raise


async def answer(user_id: int, question: str) -> str:
    """Chat hỏi–đáp (v1)."""
    return await complete(user_id, question, AI_SYSTEM_PROMPT)


# ---------------- v2: phân tích theo dịch vụ ----------------

def build_news_prompt(items: list[dict], n: int = 15) -> str:
    titles = [f"- {it['title']}" for it in items[:n] if it.get("title")]
    body = "\n".join(titles)
    return (
        "Dưới đây là các tiêu đề tin mới nhất. Hãy tóm tắt thành 5-7 gạch đầu dòng "
        "về những chủ đề nổi bật nhất hôm nay, mỗi dòng 1 câu ngắn:\n\n" + body
    )


def build_gold_prompt(items: list[dict], n: int = 8) -> str:
    lines = [
        f"- {it['name']}: mua {it['buy']:,}đ / bán {it['sell']:,}đ".replace(",", ".")
        for it in items[:n]
    ]
    body = "\n".join(lines)
    return (
        "Đây là bảng giá vàng hiện tại (VND/lượng). Hãy nhận xét ngắn gọn: loại nào cao/thấp, "
        "chênh lệch mua-bán, và một vài lưu ý cho người quan tâm:\n\n" + body
    )


def build_crypto_prompt(symbol: str, data: dict) -> str:
    return (
        f"Cặp {symbol}: giá hiện tại {data['price']:,}, biến động 24h {data['change_pct']:+.2f}%. "
        "Hãy nhận định ngắn gọn về diễn biến 24h này và tâm lý thị trường ngắn hạn."
    ).replace(",", ".")


async def summarize_news(user_id: int) -> str:
    items = await news.get_news()
    if not items:
        raise NoDataError("Chưa lấy được tin tức.")
    return await complete(user_id, build_news_prompt(items), AI_SYSTEM_PROMPT)


async def analyze_gold(user_id: int) -> str:
    items = await gold.get_gold_prices()
    if not items:
        raise NoDataError("Chưa lấy được giá vàng.")
    return await complete(user_id, build_gold_prompt(items), ANALYST_SYSTEM_PROMPT)


async def analyze_crypto(user_id: int, symbol: str) -> str:
    data = await crypto.get_price(symbol)
    if not data:
        raise NoDataError(f"Không tìm thấy cặp {symbol}.")
    return await complete(user_id, build_crypto_prompt(symbol, data), ANALYST_SYSTEM_PROMPT)
