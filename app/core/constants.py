"""Hằng số dùng chung."""

# Các module tính năng SaaS (khớp module_key trong DB)
MODULE_KEYS: list[str] = ["schedule", "gold", "crypto", "football", "news", "ai"]

MODULE_LABELS: dict[str, str] = {
    "schedule": "📅 Lịch cá nhân",
    "gold": "🥇 Giá vàng SJC/PNJ",
    "crypto": "₿ Cảnh báo Crypto",
    "football": "⚽ Bóng đá / Live score",
    "news": "📰 Tin tức nóng",
    "ai": "🤖 Trợ lý AI",
}

# Module bật SẴN cho mọi tài khoản mới tạo (tính năng nền ai cũng có).
DEFAULT_MODULES: list[str] = ["schedule"]

USER_STATUSES: list[str] = ["active", "expired", "banned"]

# Tên gói cước (trường User.plan) — chỉ là NHÃN hạng, không điều khiển module.
PLANS: list[str] = ["free", "vip"]

# Gói dịch vụ định nghĩa sẵn: bó nhiều module để bật cùng lúc.
# Sửa danh sách này để chia gói theo từng bộ phận / nhu cầu bán hàng.
# Mỗi gói: key (định danh), label (hiển thị), modules (các module_key sẽ bật).
PACKAGES: list[dict] = [
    {"key": "full", "label": "🎯 Gói Full", "modules": list(MODULE_KEYS)},
    {"key": "finance", "label": "💰 Gói Tài chính", "modules": ["gold", "crypto"]},
    {"key": "sport", "label": "⚽ Gói Thể thao", "modules": ["football"]},
    {"key": "info", "label": "📰 Gói Thông tin", "modules": ["news", "schedule"]},
]

PACKAGES_BY_KEY: dict[str, dict] = {p["key"]: p for p in PACKAGES}

# ===== Bán gói trong bot (thanh toán SePay) =====
SUBSCRIPTION_DAYS: int = 30  # mỗi lần mua có hạn 30 ngày
ORDER_TTL_MINUTES: int = 15  # QR/đơn hết hiệu lực hiển thị sau 15 phút

SERVICE_PRICE: int = 20_000
COMBO_PRICE: int = 40_000
FULL_PRICE: int = 80_000  # Full = 5 dịch vụ (gồm cả AI)

PAID_MODULES: list[str] = ["gold", "crypto", "football", "news", "ai"]

# Giới hạn số câu hỏi AI mỗi user/ngày (bảo vệ quota Gemini free).
AI_DAILY_LIMIT: int = 30

# Danh mục tin tức (RSS chuyên mục VNExpress). key = định danh lưu DB, label = hiển thị.
NEWS_CATEGORIES: list[dict] = [
    {"key": "thoisu", "label": "Thời sự", "rss": "https://vnexpress.net/rss/thoi-su.rss"},
    {"key": "thegioi", "label": "Thế giới", "rss": "https://vnexpress.net/rss/the-gioi.rss"},
    {"key": "kinhdoanh", "label": "Kinh doanh", "rss": "https://vnexpress.net/rss/kinh-doanh.rss"},
    {"key": "thethao", "label": "Thể thao", "rss": "https://vnexpress.net/rss/the-thao.rss"},
    {"key": "congnghe", "label": "Công nghệ", "rss": "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"},
    {"key": "giaitri", "label": "Giải trí", "rss": "https://vnexpress.net/rss/giai-tri.rss"},
    {"key": "phapluat", "label": "Pháp luật", "rss": "https://vnexpress.net/rss/phap-luat.rss"},
    {"key": "suckhoe", "label": "Sức khỏe", "rss": "https://vnexpress.net/rss/suc-khoe.rss"},
]

NEWS_CATEGORY_KEYS: list[str] = [c["key"] for c in NEWS_CATEGORIES]
NEWS_CATEGORY_LABELS: dict[str, str] = {c["key"]: c["label"] for c in NEWS_CATEGORIES}


# Đồng coin có lệnh riêng (vd /btc). Khoá = tên lệnh (không dấu), giá trị = CoinGecko id.
COIN_IDS: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "bnb": "binancecoin",
    "sol": "solana",
    "xrp": "ripple",
    "doge": "dogecoin",
    "ada": "cardano",
    "ton": "the-open-network",
}

# Ký hiệu đồng cho checkbox cấu hình báo giá crypto (BTC…TON).
CRYPTO_SYMBOLS: list[str] = [k.upper() for k in COIN_IDS]

# Giải bóng đá cho cấu hình báo kết quả (mã football-data.org + tên hiển thị).
FOOTBALL_LEAGUES: list[dict] = [
    {"code": "PL", "label": "Ngoại hạng Anh"},
    {"code": "PD", "label": "La Liga"},
    {"code": "SA", "label": "Serie A"},
    {"code": "BL1", "label": "Bundesliga"},
    {"code": "FL1", "label": "Ligue 1"},
    {"code": "CL", "label": "Champions League"},
]
FOOTBALL_LEAGUE_CODES: list[str] = [x["code"] for x in FOOTBALL_LEAGUES]
FOOTBALL_LEAGUE_LABELS: dict[str, str] = {x["code"]: x["label"] for x in FOOTBALL_LEAGUES}

# Sản phẩm bán được. `modules` = các module_key sẽ được BẬT khi thanh toán.
PRODUCTS: list[dict] = [
    {"key": "gold", "label": "🥇 Giá vàng", "type": "single", "modules": ["gold"], "price": SERVICE_PRICE},
    {"key": "crypto", "label": "₿ Crypto", "type": "single", "modules": ["crypto"], "price": SERVICE_PRICE},
    {"key": "football", "label": "⚽ Bóng đá", "type": "single", "modules": ["football"], "price": SERVICE_PRICE},
    {"key": "news", "label": "📰 Tin tức", "type": "single", "modules": ["news"], "price": SERVICE_PRICE},
    {"key": "ai", "label": "🤖 Trợ lý AI", "type": "single", "modules": ["ai"], "price": SERVICE_PRICE},
    {"key": "combo_finance", "label": "💰 Combo Tài chính", "type": "combo", "modules": ["gold", "crypto"], "price": COMBO_PRICE},
    {"key": "combo_entertain", "label": "🎬 Combo Giải trí", "type": "combo", "modules": ["football", "news"], "price": COMBO_PRICE},
    {"key": "full", "label": "🎯 Full 5 dịch vụ", "type": "full", "modules": list(PAID_MODULES), "price": FULL_PRICE},
]

PRODUCTS_BY_KEY: dict[str, dict] = {p["key"]: p for p in PRODUCTS}
