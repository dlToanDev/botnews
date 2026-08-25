"""Handlers module SaaS: Crypto, Vàng, Bóng đá, Tin tức (dữ liệu real-time)."""
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.decorators import require_module
from app.core.timeutils import now_local
from app.integrations import crypto, football, gold, news
from app.services import settings_service


def _fmt_vnd(n: int) -> str:
    return f"{n:,.0f}".replace(",", ".")


# ---------------- Crypto ----------------

@require_module("crypto")
async def crypto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    symbol = (context.args[0].upper() if context.args else "BTCUSDT")
    data = await crypto.get_price(symbol)
    if not data:
        await update.message.reply_text(f"❓ Không tìm thấy cặp `{symbol}` trên Binance.", parse_mode=ParseMode.MARKDOWN)
        return
    arrow = "🟢▲" if data["change_pct"] >= 0 else "🔴▼"
    await update.message.reply_text(
        f"*{symbol}*\n💵 Giá: `{data['price']:,}`\n{arrow} 24h: `{data['change_pct']:+.2f}%`",
        parse_mode=ParseMode.MARKDOWN,
    )


@require_module("crypto")
async def setcrypto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2 or not context.args[1].replace(".", "").isdigit():
        await update.message.reply_text(
            "✍️ Cú pháp: `/setcrypto BTCUSDT 5` (cảnh báo khi biến động ≥ 5%/24h)",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    symbol, pct = context.args[0].upper(), float(context.args[1])
    wl = await settings_service.add_crypto_watch(update.effective_user.id, symbol, pct)
    lines = "\n".join(f"• {w['symbol']} ≥ {w['threshold_pct']}%" for w in wl)
    await update.message.reply_text(f"✅ Đã cập nhật watchlist:\n{lines}")


# ---------------- Gold ----------------

@require_module("gold")
async def gold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = await gold.get_gold_prices()
    if not items:
        await update.message.reply_text("⚠️ Chưa lấy được giá vàng, thử lại sau.")
        return
    lines = []
    for it in items[:6]:
        lines.append(f"*{it['name']}*\n  Mua `{_fmt_vnd(it['buy'])}` / Bán `{_fmt_vnd(it['sell'])}`")
    await update.message.reply_text(
        "🥇 *Giá vàng (VND/lượng)*\n" + "\n".join(lines), parse_mode=ParseMode.MARKDOWN
    )


# ---------------- Football ----------------

@require_module("football")
async def football_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not football.is_configured():
        await update.message.reply_text("⚙️ Admin chưa cấu hình API bóng đá (API_FOOTBALL_KEY).")
        return
    date_str = now_local().strftime("%Y-%m-%d")
    fixtures = await football.get_fixtures(date_str)
    if not fixtures:
        await update.message.reply_text("📭 Hôm nay không có trận nào (hoặc chưa có dữ liệu).")
        return
    lines = []
    for f in fixtures[:15]:
        score = ""
        if f["home_goals"] is not None:
            score = f" `{f['home_goals']}-{f['away_goals']}` ({f['status']})"
        lines.append(f"⚽ {f['home']} vs {f['away']}{score}")
    await update.message.reply_text("*Lịch/Kết quả hôm nay:*\n" + "\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@require_module("football")
async def setteam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("✍️ Cú pháp: `/setteam Arsenal`", parse_mode=ParseMode.MARKDOWN)
        return
    team = " ".join(context.args)
    teams = await settings_service.add_favorite_team(update.effective_user.id, team)
    await update.message.reply_text("✅ Đội theo dõi: " + ", ".join(teams))


# ---------------- News ----------------

@require_module("news")
async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = await news.get_news()
    if not items:
        await update.message.reply_text("⚠️ Chưa lấy được tin, thử lại sau.")
        return
    lines = [f"• [{it['title']}]({it['link']})" for it in items[:5]]
    await update.message.reply_text(
        "📰 *Tin mới nhất:*\n" + "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


@require_module("news")
async def setnews_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "✍️ Cú pháp: `/setnews bitcoin,fed,vn-index`", parse_mode=ParseMode.MARKDOWN
        )
        return
    raw = " ".join(context.args)
    keywords = [k.strip() for k in raw.split(",") if k.strip()]
    kws = await settings_service.set_news_keywords(update.effective_user.id, keywords)
    await update.message.reply_text("✅ Từ khoá tin tức: " + ", ".join(kws))
