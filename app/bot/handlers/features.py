"""Handlers module SaaS: Crypto, Vàng, Bóng đá, Tin tức (dữ liệu real-time)."""
from datetime import datetime, timezone

from telegram import InputMediaPhoto, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.decorators import require_module
from app.core.constants import (
    COIN_IDS,
    NEWS_CATEGORIES,
    NEWS_CATEGORY_KEYS,
    NEWS_CATEGORY_LABELS,
)
from app.core.timeutils import fmt_local, now_local
from app.integrations import coingecko, football, football_data, gold, news
from app.services import gold_service, settings_service


def _fmt_vnd(n: int) -> str:
    return f"{n:,.0f}".replace(",", ".")


# ---------------- Crypto ----------------

# Biểu tượng riêng cho từng đồng (mặc định 🪙 nếu chưa có).
_COIN_ICON: dict[str, str] = {
    "BTC": "₿", "ETH": "Ξ", "BNB": "🔶", "SOL": "◎",
    "XRP": "✕", "DOGE": "Ð", "ADA": "₳", "TON": "💎",
}


def _icon(symbol: str) -> str:
    return _COIN_ICON.get(symbol, "🪙")


def _fmt_usd(v) -> str:
    """Giá USD: ≥1000 không số lẻ, ≥1 hai số lẻ, <1 bốn số lẻ."""
    if v is None:
        return "N/A"
    if v >= 1000:
        return f"${v:,.0f}"
    if v >= 1:
        return f"${v:,.2f}"
    return f"${v:,.4f}"


def _fmt_compact(v) -> str:
    """Rút gọn T/B/M cho vốn hóa & volume."""
    if v is None:
        return "N/A"
    if v >= 1e12:
        return f"${v / 1e12:.2f}T"
    if v >= 1e9:
        return f"${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"${v / 1e6:.2f}M"
    return f"${v:,.0f}"


def format_coin(d: dict) -> str:
    """Tin nhắn 1 đồng — kiểu Card sang (Markdown, chỉ số căn cột trong khối code)."""
    head = f"{_icon(d['symbol'])} *{d['name']}* · {d['symbol']}"
    if d.get("rank"):
        head += f"  ·  #{d['rank']}"
    pct = d.get("change_pct") or 0
    arrow = "🟢" if pct >= 0 else "🔴"

    def row(emoji: str, label: str, value: str) -> str:
        return f"{emoji} {label:<8}{value}"

    rows = [
        row("💵", "Giá", _fmt_usd(d.get("price_usd"))),
    ]
    if d.get("price_vnd"):
        rows.append(row("🇻🇳", "VND", f"{_fmt_vnd(d['price_vnd'])} ₫"))
    rows += [
        row(arrow, "24h", f"{pct:+.2f}%"),
        "",
        row("📈", "Đỉnh", _fmt_usd(d.get("high_usd"))),
        row("📉", "Đáy", _fmt_usd(d.get("low_usd"))),
        row("🏦", "Vốn hóa", _fmt_compact(d.get("market_cap"))),
        row("📊", "Volume", _fmt_compact(d.get("volume"))),
    ]
    return f"{head}\n```\n" + "\n".join(rows) + "\n```"


def format_top(coins: list[dict]) -> str:
    """Danh sách top vốn hóa — bảng canh cột (khối monospace)."""
    rows = []
    for c in coins:
        pct = c.get("change_pct") or 0
        arrow = "🟢" if pct >= 0 else "🔴"
        rows.append(
            f"{c.get('rank', 0):>2}. {c['symbol']:<5} "
            f"{_fmt_usd(c.get('price_usd')):>11}  {arrow} {pct:+.2f}%"
        )
    return "🔥 *TOP VỐN HÓA*\n```\n" + "\n".join(rows) + "\n```"


@require_module("crypto")
async def crypto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Không tham số → top vốn hóa. Có tham số → tra 1 đồng (nhận symbol hoặc CoinGecko id).
    if not context.args:
        coins = await coingecko.get_top(10)
        if not coins:
            await update.message.reply_text("⚠️ Chưa lấy được dữ liệu, thử lại sau.")
            return
        await update.message.reply_text(format_top(coins), parse_mode=ParseMode.MARKDOWN)
        return

    arg = context.args[0].lower()
    coin_id = COIN_IDS.get(arg, arg)
    data = await coingecko.get_coin(coin_id)
    if not data:
        await update.message.reply_text(f"❓ Không tìm thấy đồng `{arg}`.", parse_mode=ParseMode.MARKDOWN)
        return
    await update.message.reply_text(format_coin(data), parse_mode=ParseMode.MARKDOWN)


def make_coin_cmd(coin_id: str):
    """Sinh handler cho 1 đồng cố định (vd /btc)."""

    @require_module("crypto")
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        data = await coingecko.get_coin(coin_id)
        if not data:
            await update.message.reply_text("⚠️ Chưa lấy được dữ liệu, thử lại sau.")
            return
        await update.message.reply_text(format_coin(data), parse_mode=ParseMode.MARKDOWN)

    return handler


# Handler dựng sẵn cho từng đồng (khoá = tên lệnh, vd "btc").
COIN_HANDLERS = {sym: make_coin_cmd(coin_id) for sym, coin_id in COIN_IDS.items()}


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
    text = gold_service.format_gold_prices(items, now_local().strftime("%H:%M %d/%m"))
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ---------------- Football ----------------

def _kickoff(ts: int | None) -> str:
    """Unix timestamp → giờ địa phương (chuỗi ngắn)."""
    if not ts:
        return ""
    return fmt_local(datetime.fromtimestamp(ts, tz=timezone.utc), "%H:%M %d/%m")


def _match_tag(f: dict) -> str:
    """Nhãn cuối dòng: phút/trạng thái nếu đã/đang đá, ngược lại là giờ bóng lăn."""
    if f["home_goals"] is not None:
        return f"{f['elapsed']}'" if f.get("elapsed") else (f.get("status") or "")
    return _kickoff(f.get("timestamp"))


def _fixtures_block(items: list[dict]) -> str:
    """Danh sách trận dạng bảng canh cột: chủ nhà phải · tỉ số · khách trái · nhãn."""
    rows = []
    for f in items:
        home = (f["home"] or "")[:14]
        away = (f["away"] or "")[:14]
        score = f"{f['home_goals']}-{f['away_goals']}" if f["home_goals"] is not None else "vs"
        line = f"{home:>14} {score:^5} {away:<14} {_match_tag(f)}"
        rows.append(line.rstrip())
    return "```\n" + "\n".join(rows) + "\n```"


def _standings_block(table: list[dict], limit: int = 20) -> str:
    """BXH dạng bảng canh cột (khối monospace) — thẳng hàng, đẹp trên Telegram."""
    header = f"{'#':>2}  {'Đội':<14} {'Tr':>2} {'HS':>3} {'Đ':>3}"
    rows = [header, "─" * 28]
    for r in table[:limit]:
        name = (r.get("team") or "")[:14]
        rows.append(
            f"{r.get('rank', 0):>2}  {name:<14} "
            f"{r.get('played', 0):>2} {r.get('goals_diff', 0):>+3} {r.get('points', 0):>3}"
        )
    return "```\n" + "\n".join(rows) + "\n```"


def _results_block(matches: list[dict]) -> str:
    """Danh sách trận dạng bảng canh cột: chủ nhà phải · tỉ số · khách trái."""
    rows = []
    for m in matches:
        home = (m["home"] or "")[:14]
        away = (m["away"] or "")[:14]
        score = f"{m['home_goals']}-{m['away_goals']}" if m["home_goals"] is not None else "vs"
        rows.append(f"{home:>14} {score:^5} {away}")
    return "```\n" + "\n".join(rows) + "\n```"


async def _guard_configured(update: Update) -> bool:
    if not football.is_configured():
        await update.message.reply_text("⚙️ Admin chưa cấu hình API bóng đá (API_FOOTBALL_KEY).")
        return False
    return True


@require_module("football")
async def football_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_configured(update):
        return
    date_str = now_local().strftime("%Y-%m-%d")
    fixtures = await football.get_fixtures(date_str)
    if not fixtures:
        await update.message.reply_text("📭 Hôm nay không có trận nào (hoặc chưa có dữ liệu).")
        return
    await update.message.reply_text(
        "📅 *Lịch/Kết quả hôm nay:*\n" + _fixtures_block(fixtures[:15]), parse_mode=ParseMode.MARKDOWN
    )


@require_module("football")
async def live_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_configured(update):
        return
    live = await football.get_live_fixtures()
    if not live:
        await update.message.reply_text("😴 Hiện không có trận nào đang diễn ra.")
        return
    await update.message.reply_text(
        "🔴 *Đang diễn ra:*\n" + _fixtures_block(live[:20]), parse_mode=ParseMode.MARKDOWN
    )


@require_module("football")
async def standings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_configured(update):
        return
    if not context.args or not context.args[0].isdigit():
        popular = "\n".join(f"• `{lid}` — {name}" for lid, name in football.POPULAR_LEAGUES.items())
        await update.message.reply_text(
            "✍️ Cú pháp: `/bxh <league_id>` (vd `/bxh 39`)\n\n*Giải phổ biến:*\n" + popular,
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    data = await football.get_standings(int(context.args[0]))
    table = data.get("table") or []
    if not table:
        await update.message.reply_text("📭 Chưa có BXH cho giải/mùa này.")
        return
    await update.message.reply_text(
        f"🏆 *BXH {data.get('league') or ''}*\n" + _standings_block(table),
        parse_mode=ParseMode.MARKDOWN,
    )


@require_module("football")
async def myteam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard_configured(update):
        return
    teams = await settings_service.get_favorite_teams(update.effective_user.id)
    if not teams:
        await update.message.reply_text(
            "🙅 Bạn chưa theo dõi đội nào. Dùng `/setteam Arsenal` để thêm.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    blocks = []
    for name in teams:
        found = await football.search_team(name)
        if not found:
            blocks.append(f"*{name}*\n  ❓ Không tra được id đội.")
            continue
        team = found[0]
        fixtures = await football.get_team_fixtures(team["id"], upcoming=True, count=3)
        if not fixtures:
            blocks.append(f"*{team['name']}*\n  📭 Chưa có lịch sắp tới.")
            continue
        blocks.append(f"*{team['name']}*\n{_fixtures_block(fixtures)}")
    await update.message.reply_text("📅 *Lịch đội theo dõi:*\n\n" + "\n\n".join(blocks), parse_mode=ParseMode.MARKDOWN)


@require_module("football")
async def setteam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("✍️ Cú pháp: `/setteam Arsenal`", parse_mode=ParseMode.MARKDOWN)
        return
    query = " ".join(context.args)
    # Validate qua API để lưu tên chuẩn (khớp được với live/lịch). Nếu chưa cấu hình
    # API thì vẫn cho lưu tên thô để không chặn người dùng.
    name = query
    if football.is_configured():
        found = await football.search_team(query)
        if not found:
            await update.message.reply_text(f"❓ Không tìm thấy đội `{query}`. Thử tên tiếng Anh.", parse_mode=ParseMode.MARKDOWN)
            return
        name = found[0]["name"]
    teams = await settings_service.add_favorite_team(update.effective_user.id, name)
    await update.message.reply_text("✅ Đội theo dõi: " + ", ".join(teams))


# ---------------- Lệnh tắt theo giải (football-data.org, mùa hiện tại) ----------------
# Mỗi giải sinh 2 lệnh: /<cmd> = kết quả vòng gần nhất, /bxh<cmd> = BXH.
# tên_lệnh → (mã football-data, tên tiếng Việt)
LEAGUE_CMDS: dict[str, tuple[str, str]] = {
    "epl": ("PL", "Ngoại hạng Anh"),
    "laliga": ("PD", "La Liga"),
    "seria": ("SA", "Serie A"),
    "bundes": ("BL1", "Bundesliga"),
    "ligue1": ("FL1", "Ligue 1"),
    "c1": ("CL", "Champions League"),
}


async def _guard_fd(update: Update) -> bool:
    if not football_data.is_configured():
        await update.message.reply_text(
            "⚙️ Admin chưa cấu hình API kết quả/BXH (FOOTBALL_DATA_KEY)."
        )
        return False
    return True


def _make_results_handler(code: str, label: str):
    @require_module("football")
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _guard_fd(update):
            return
        data = await football_data.get_recent_results(code)
        matches = data.get("matches") or []
        if not matches:
            await update.message.reply_text(f"📭 Chưa có kết quả *{label}* mùa này.", parse_mode=ParseMode.MARKDOWN)
            return
        title = f"⚽ *{label}* — _Vòng {data['matchday']}_"
        await update.message.reply_text(title + "\n" + _results_block(matches), parse_mode=ParseMode.MARKDOWN)

    return handler


def _make_standings_handler(code: str, label: str):
    @require_module("football")
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _guard_fd(update):
            return
        data = await football_data.get_standings(code)
        table = data.get("table") or []
        if not table:
            await update.message.reply_text(f"📭 Chưa có BXH *{label}* mùa này.", parse_mode=ParseMode.MARKDOWN)
            return
        await update.message.reply_text(
            f"🏆 *BXH {data.get('league') or label}*\n" + _standings_block(table),
            parse_mode=ParseMode.MARKDOWN,
        )

    return handler


# Handler dựng sẵn cho từng giải (khoá = tên lệnh, không dấu).
LEAGUE_RESULT_HANDLERS = {cmd: _make_results_handler(code, label) for cmd, (code, label) in LEAGUE_CMDS.items()}
LEAGUE_STANDINGS_HANDLERS = {cmd: _make_standings_handler(code, label) for cmd, (code, label) in LEAGUE_CMDS.items()}


# ---------------- News ----------------

NEWS_PER_CMD = 3  # số tin hiển thị mỗi lần /news


def _news_caption(it: dict) -> str:
    return f"📰 *{it['title']}*\n[Đọc bài »]({it['link']})"


def _pick_news(items: list[dict], category: str | None, limit: int) -> list[dict]:
    """Lọc theo loại (None = tất cả), chỉ lấy tin CÓ ẢNH, tối đa `limit`."""
    out = []
    for it in items:
        if category and it.get("category") != category:
            continue
        if not it.get("image"):
            continue
        out.append(it)
        if len(out) >= limit:
            break
    return out


@require_module("news")
async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    category = None
    if context.args:
        arg = context.args[0].lower()
        if arg not in NEWS_CATEGORY_KEYS:
            opts = "\n".join(f"• `{c['key']}` — {c['label']}" for c in NEWS_CATEGORIES)
            await update.message.reply_text(
                f"❓ Loại tin `{arg}` không hợp lệ.\n\n*Các loại:*\n{opts}\n\nVí dụ: `/news thethao`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        category = arg

    items = await news.get_news()
    if not items:
        await update.message.reply_text("⚠️ Chưa lấy được tin, thử lại sau.")
        return

    label = NEWS_CATEGORY_LABELS.get(category, "mới nhất") if category else "mới nhất"
    picked = _pick_news(items, category, NEWS_PER_CMD)
    if picked:
        try:
            media = [
                InputMediaPhoto(media=it["image"], caption=_news_caption(it),
                                parse_mode=ParseMode.MARKDOWN)
                for it in picked
            ]
            await update.message.reply_media_group(media=media)
            return
        except Exception:  # noqa: BLE001 — ảnh lỗi → fallback danh sách chữ
            pass

    subset = [it for it in items if not category or it.get("category") == category][:5]
    if not subset:
        await update.message.reply_text("📭 Chưa có tin cho loại này.")
        return
    lines = [f"• [{it['title']}]({it['link']})" for it in subset]
    await update.message.reply_text(
        f"📰 *Tin {label}:*\n" + "\n".join(lines),
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
