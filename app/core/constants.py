"""Hằng số dùng chung."""

# Các module tính năng SaaS (khớp module_key trong DB)
MODULE_KEYS: list[str] = ["schedule", "gold", "crypto", "football", "news"]

MODULE_LABELS: dict[str, str] = {
    "schedule": "📅 Lịch cá nhân",
    "gold": "🥇 Giá vàng SJC/PNJ",
    "crypto": "₿ Cảnh báo Crypto",
    "football": "⚽ Bóng đá / Live score",
    "news": "📰 Tin tức nóng",
}

USER_STATUSES: list[str] = ["active", "expired", "banned"]
