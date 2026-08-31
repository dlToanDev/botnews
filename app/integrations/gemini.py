"""Adapter Google Gemini — REST generateContent (trợ lý AI)."""
import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiError(Exception):
    """Lỗi chung khi gọi Gemini."""


class GeminiQuotaError(GeminiError):
    """Hết quota (HTTP 429)."""


async def ask(prompt: str, system: str | None = None) -> str:
    """Hỏi Gemini một câu (single-turn). Trả về text; ném GeminiError khi lỗi."""
    if not settings.GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY chưa cấu hình")

    # Gộp system prompt vào nội dung để tránh phụ thuộc field systemInstruction.
    text = f"{system}\n\nNgười dùng hỏi: {prompt}" if system else prompt
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"maxOutputTokens": 800, "temperature": 0.7},
    }
    url = _URL.format(model=settings.GEMINI_MODEL)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=body)
    except httpx.HTTPError as e:
        logger.warning("Gemini lỗi mạng: %s", e)
        raise GeminiError("Lỗi kết nối tới AI") from e

    if resp.status_code == 429:
        raise GeminiQuotaError("Gemini hết quota")
    if resp.status_code != 200:
        logger.warning("Gemini HTTP %s: %s", resp.status_code, resp.text[:300])
        raise GeminiError(f"Gemini lỗi {resp.status_code}")

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        # Không có ứng viên → thường do bị chặn an toàn.
        raise GeminiError("AI không trả lời được câu này (có thể bị chặn nội dung)")
    parts = candidates[0].get("content", {}).get("parts", [])
    answer = "".join(p.get("text", "") for p in parts).strip()
    if not answer:
        raise GeminiError("AI trả về rỗng")
    return answer
