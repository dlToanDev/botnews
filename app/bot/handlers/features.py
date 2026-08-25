"""Stub handlers cho các module SaaS (Phase 3 sẽ tích hợp API thật).

Mục đích Phase 2: chứng minh cơ chế phân quyền @require_module hoạt động —
user chỉ vào được khi Admin đã bật module tương ứng.
"""
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.decorators import require_module


@require_module("crypto")
async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("₿ (demo) Module Crypto đã bật — dữ liệu real-time sẽ có ở Phase 3.")


@require_module("gold")
async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🥇 (demo) Module Giá vàng đã bật — dữ liệu SJC/PNJ sẽ có ở Phase 3.")


@require_module("football")
async def football(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⚽ (demo) Module Bóng đá đã bật — live score sẽ có ở Phase 3.")


@require_module("news")
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📰 (demo) Module Tin tức đã bật — tin nóng sẽ có ở Phase 3.")
