# Thiết kế: Lệnh crypto theo từng đồng + top vốn hóa

**Ngày:** 2026-08-28
**Nhánh:** feat/web-admin-redesign

## Mục tiêu

Nâng cấp tính năng crypto của bot Telegram:

- Lệnh riêng cho từng đồng phổ biến: `/btc`, `/eth`, `/bnb`, `/sol`, `/xrp`, `/doge`, `/ada`, `/ton` — gõ ra là hiện giá đồng đó.
- Lệnh `/crypto` (không tham số) → hiện **top 10 đồng theo vốn hóa**.
- Mỗi đồng hiển thị: giá USD + VND, %24h, đỉnh/đáy 24h, vốn hóa, volume 24h.

## Quyết định thiết kế

Dùng **CoinGecko API** (miễn phí, không cần key) cho các lệnh mới, vì Binance
(nguồn hiện tại) không cung cấp vốn hóa, giá VND, và ranking theo vốn hóa.

Hệ thống cảnh báo watchlist hiện có (`/setcrypto`, `crypto_alert` worker) **giữ
nguyên trên Binance** — không đụng tới. Chỉ thêm nguồn mới cho các lệnh tra cứu.

## Kiến trúc

### 1. Integration mới: `app/integrations/coingecko.py`

Theo pattern `BaseAdapter` (cache Redis TTL 60s, retry, stale fallback) như
`app/integrations/crypto.py`.

Endpoint dùng: `GET https://api.coingecko.com/api/v3/coins/markets`
tham số: `vs_currency`, `ids` (hoặc `order=market_cap_desc` cho top),
`price_change_percentage=24h`.

**Adapter:** một subclass nhận tham số trong `__init__` để đặt `name` cache riêng
cho từng biến thể (usd / vnd / top), vì `BaseAdapter.name` là khóa cache cố định.

```python
class CoinMarketsAdapter(BaseAdapter):
    ttl = 60
    def __init__(self, cache_key: str, params: dict):
        self.name = f"crypto:coingecko:{cache_key}"
        self.params = params
    async def fetch(self):
        return await http_get_json(COINGECKO_MARKETS, params=self.params)
```

**API công khai của module:**

- `async def get_coin(coin_id: str) -> dict | None`
  Trả về dict đã chuẩn hóa cho 1 đồng:
  `{name, symbol, price_usd, price_vnd, change_pct, high_usd, low_usd, market_cap, volume, rank}`.
  Lấy dữ liệu bằng cách gọi 2 adapter (usd + vnd) cho **cả nhóm đồng ta theo dõi
  một lần** (ids = tất cả `COIN_IDS.values()`), cache lại, rồi trích ra `coin_id`.
  Trả `None` nếu không tìm thấy.

- `async def get_top(limit: int = 10) -> list[dict]`
  Top N theo vốn hóa (`order=market_cap_desc&per_page=limit`), mỗi phần tử:
  `{rank, name, symbol, price_usd, change_pct}`.

Giá USD và VND lấy từ 2 lần gọi `vs_currency=usd` và `vs_currency=vnd`; chạy
song song bằng `asyncio.gather`. Cache 60s nên tổng tải lên CoinGecko rất thấp,
nằm trong giới hạn free (~30 lần/phút).

### 2. Constants: `app/core/constants.py`

Bảng ánh xạ symbol → CoinGecko id (cũng là danh sách 8 đồng có lệnh riêng):

```python
COIN_IDS = {
    "btc": "bitcoin", "eth": "ethereum", "bnb": "binancecoin",
    "sol": "solana", "xrp": "ripple", "doge": "dogecoin",
    "ada": "cardano", "ton": "the-open-network",
}
```

### 3. Handlers: `app/bot/handlers/features.py`

- **`format_coin(data: dict) -> str`** — hàm format dùng chung, trả HTML.
  Kiểu **Card sang**: dòng tiêu đề đậm, đường kẻ phân cách, phần chỉ số căn cột
  đặt trong khối monospace (`<pre>`) để các cột thẳng hàng trên mọi thiết bị.

  ```
  ₿  Bitcoin · BTC              #1
  ━━━━━━━━━━━━━━━━━━━━━
  💵  Giá      $67,234
  🇻🇳  VND      1.712.345.678 ₫
  🟢  24h      +2.34%

  📈  Đỉnh     $68,100
  📉  Đáy      $65,900
  🏦  Vốn hóa  $1.33T
  📊  Volume   $28.5B
  ```

  Dùng `ParseMode.HTML`. `🟢` khi %24h ≥ 0, `🔴` khi < 0.

- **`format_top(coins: list[dict]) -> str`** — danh sách top 10, cùng phong cách:

  ```
  🔥  TOP 10 VỐN HÓA
  ━━━━━━━━━━━━━━━━━━━━━
  1.  ₿ BTC    $67,234    🟢 +2.34%
  2.  Ξ ETH    $3,512     🔴 −1.20%
  ...
  ```

- **Helper format số** (đặt trong `features.py` hoặc `app/core/format.py`):
  - `fmt_usd(v)` — `$` + phân cách nghìn; ≥1 → không/2 số lẻ tùy độ lớn, <1 → 4 số lẻ.
  - `fmt_vnd(v)` — số nguyên, phân cách nghìn bằng dấu chấm, hậu tố `₫`.
  - `fmt_compact(v)` — rút gọn T/B/M (vốn hóa, volume).

- **Factory tạo lệnh từng đồng** (tránh 8 hàm trùng lặp):

  ```python
  def make_coin_cmd(coin_id: str):
      @require_module("crypto")
      async def handler(update, context):
          data = await coingecko.get_coin(coin_id)
          if not data:
              await update.message.reply_text("❓ Không lấy được dữ liệu.")
              return
          await update.message.reply_text(format_coin(data), parse_mode=ParseMode.HTML)
      return handler
  ```

- **`crypto_cmd` viết lại:**
  - Không tham số → `get_top(10)` + `format_top`.
  - Có tham số (vd `/crypto sol` hoặc `/crypto btc`) → tra 1 đồng qua `get_coin`
    (nhận cả symbol trong `COIN_IDS` lẫn coin_id trực tiếp), giữ tương thích ngược.

### 4. Đăng ký lệnh: `app/bot/main.py`

- Thêm VI_ALIAS cho từng đồng, ví dụ `"btc": "bitcoin"`, `"eth": "ethereum"`…
  (bí danh tiếng Việt cho mỗi coin — dùng tên đồng).
- Vòng lặp đăng ký 8 lệnh coin từ `COIN_IDS`:
  ```python
  for sym, coin_id in COIN_IDS.items():
      app.add_handler(CommandHandler(_cmd(sym), features.make_coin_cmd(coin_id)))
  ```

### 5. Phân quyền

Mọi lệnh mới dùng `@require_module("crypto")` như lệnh cũ. User phải có gói
crypto mới dùng được. Không đổi gì ở tầng subscription.

## Xử lý lỗi

- API lỗi → BaseAdapter tự dùng cache cũ (stale) nếu có; nếu không, handler bắt
  và trả tin nhắn thân thiện `❓ Không lấy được dữ liệu, thử lại sau.`.
- Symbol/coin_id không hợp lệ ở `/crypto <arg>` → `❓ Không tìm thấy đồng này.`.

## Kiểm thử

- Unit test `coingecko.get_coin` / `get_top` với HTTP mock (dựng response
  CoinGecko mẫu) — kiểm tra chuẩn hóa field và ghép USD+VND.
- Unit test các helper format (`fmt_usd`, `fmt_vnd`, `fmt_compact`, `format_coin`,
  `format_top`) với giá trị biên: giá <1, số âm %24h, vốn hóa hàng nghìn tỷ.
- Test factory `make_coin_cmd` trả handler gọi đúng coin_id (mock update/context).

## Ngoài phạm vi (YAGNI)

- Không đổi hệ thống cảnh báo watchlist Binance.
- Không thêm biểu đồ, không lệnh động cho mọi symbol tùy ý (chỉ 8 đồng cố định
  + fallback `/crypto <arg>`).
- Không thêm nút inline chuyển đổi trending/gainers.
