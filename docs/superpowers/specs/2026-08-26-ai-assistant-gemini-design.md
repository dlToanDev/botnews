# Trợ lý AI trong bot (Gemini) — v1

Ngày: 2026-08-26 · Nhánh: `feat/web-admin-redesign` (nối tiếp)

## Mục tiêu (v1)
Thêm **trợ lý chat hỏi–đáp** dùng Google Gemini, bán như **module trả phí `ai`**.
Lệnh `/ai <câu hỏi>` → Gemini trả lời tiếng Việt. Giới hạn 30 câu/user/ngày.

Ngoài phạm vi v1: nhớ ngữ cảnh nhiều lượt; tóm tắt/phân tích dịch vụ (v2);
hiểu ngôn ngữ tự nhiên → tự gọi lệnh (v3).

## Gemini (đã xác nhận)
- Model `gemini-2.0-flash`, REST:
  `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={KEY}`
- Free: 15 req/phút, 1.500 req/ngày (toàn tài khoản). Body `{"contents":[{"parts":[{"text":...}]}]}`.

## Catalog / module
- Thêm module `ai` (🤖 Trợ lý AI) vào `MODULE_KEYS`, `MODULE_LABELS`.
- `PAID_MODULES` += `ai` (⇒ Full gồm 5 dịch vụ).
- `PRODUCTS`: thêm `{key:"ai", single, 20k}`; sửa `full` modules gồm `ai`, `FULL_PRICE=80_000`.
- Không đụng combo hiện có.

## Thành phần
1. **Config** (`config.py` + `.env.example`): `GEMINI_API_KEY` (str|None), `GEMINI_MODEL="gemini-2.0-flash"`.
   `ai_enabled = bool(GEMINI_API_KEY)`.
2. **Integration** `app/integrations/gemini.py`: `async ask(prompt, system) -> str`.
   httpx POST; timeout 30s. Trả text; ném lỗi rõ ràng cho 429 (hết quota), lỗi mạng, bị chặn nội dung.
3. **Quota** `app/services/ai_service.py`: dùng `redis_client`.
   - key `ai:quota:{user_id}:{YYYYMMDD}` (giờ địa phương), `INCR` + `EXPIRE` ~ 26h.
   - `check_and_incr(user_id, limit=30) -> (ok, used)`; nếu vượt → không gọi Gemini.
   - `AI_SYSTEM_PROMPT` tiếng Việt: trợ lý BotNews, trả lời ngắn gọn, lịch sự.
   - `AI_DAILY_LIMIT = 30` (constants).
4. **Bot handler** `app/bot/handlers/ai.py`: `@require_module("ai")` `ai_cmd`.
   - Không có câu hỏi → hướng dẫn cú pháp.
   - `settings.ai_enabled` sai → "AI chưa được cấu hình".
   - Quota vượt → báo "hết lượt hôm nay (30), mai thử lại".
   - Gửi `ChatAction.TYPING`, gọi `gemini.ask`, reply. Lỗi → thông báo thân thiện + log.
5. **Wiring** `bot/main.py`: `VI_ALIAS["ai"]="troly"`, thêm `_MENU_ITEMS` (🤖 Trợ lý AI),
   `CommandHandler(_cmd("ai"), ai.ai_cmd)`.

## Kiểm thử
- Unit: quota `check_and_incr` (lần 1..30 ok, 31 chặn) trên Redis thật (rollback bằng key ngày test rồi xoá);
  catalog cập nhật (full có `ai`, giá 80k, có product `ai` 20k); gemini.ask parse body giả (mock httpx).
- Gating: chưa mua `ai` → decorator chặn (đã có sẵn cơ chế).
- Nếu có `GEMINI_API_KEY` thật: gọi `gemini.ask("xin chào")` trả lời không rỗng.
- Chưa có key: `/ai` báo "chưa cấu hình" (không crash).

## Golive
Điền `GEMINI_API_KEY` (Google AI Studio → Get API key) vào `.env` → `docker compose up -d --build bot`.
