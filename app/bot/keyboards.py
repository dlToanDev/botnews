"""Bàn phím (keyboards) cho bot."""
from telegram import ReplyKeyboardMarkup

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🧭 Menu"],
        ["📅 Lịch hôm nay", "📋 Tất cả lịch"],
        ["➕ Thêm lịch", "ℹ️ Trợ giúp"],
    ],
    resize_keyboard=True,
)
