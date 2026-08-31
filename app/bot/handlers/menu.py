"""Menu inline phân cấp: mua gói + tự cấu hình dịch vụ (Vàng/Crypto/Tin tức/Bóng đá)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.bot.decorators import require_active
from app.core.constants import (
    CRYPTO_SYMBOLS,
    MODULE_KEYS,
    MODULE_LABELS,
    NEWS_CATEGORIES,
    NEWS_CATEGORY_LABELS,
    PRODUCTS,
)
from app.core.database import AsyncSessionLocal
from app.services import settings_service, subscription_service
from app.services.gold_service import parse_times
from app.services.user_service import get_or_create_user, is_active

TIME_PRESETS = ["0700", "0800", "0900", "1200", "1500", "1600", "1800", "2000", "2200"]
CONFIGURABLE = ["gold", "crypto", "news", "football"]


# ---------------- Hàm thuần ----------------

def toggle(lst: list, item) -> list:
    out = list(lst)
    if item in out:
        out.remove(item)
    else:
        out.append(item)
    return out


def hhmm_to_display(hhmm: str) -> str:
    return f"{hhmm[:2]}:{hhmm[2:]}"


def _vnd(amount: int) -> str:
    return f"{amount:,}".replace(",", ".") + "đ"


def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Mua gói dịch vụ", callback_data="menu:buy")],
        [InlineKeyboardButton("📦 Gói đã mua & Cài đặt", callback_data="menu:mine")],
        [InlineKeyboardButton("ℹ️ Trợ giúp", callback_data="menu:help")],
    ])


def build_buy_root() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Mua theo Gói (Full/Combo)", callback_data="menu:buy:pkg")],
        [InlineKeyboardButton("🧩 Mua lẻ dịch vụ", callback_data="menu:buy:single")],
        [InlineKeyboardButton("◀️ Quay lại", callback_data="menu:home")],
    ])


def build_products_kb(ptype: str) -> InlineKeyboardMarkup:
    """ptype='single' → dịch vụ lẻ; 'pkg' → combo + full. Nút dùng buy:<key>."""
    if ptype == "single":
        prods = [p for p in PRODUCTS if p["type"] == "single"]
    else:
        prods = [p for p in PRODUCTS if p["type"] in ("combo", "full")]
    rows = [
        [InlineKeyboardButton(f"{p['label']} — {_vnd(p['price'])}", callback_data=f"buy:{p['key']}")]
        for p in prods
    ]
    rows.append([InlineKeyboardButton("◀️ Quay lại", callback_data="menu:buy")])
    return InlineKeyboardMarkup(rows)


def format_owned(modules_map: dict[str, bool]) -> str:
    enabled = [MODULE_LABELS[k] for k in MODULE_KEYS if modules_map.get(k)]
    if not enabled:
        return "📦 *Gói đã mua*\n\nBạn chưa có dịch vụ nào. Bấm 🛒 Mua gói để đăng ký."
    body = "\n".join(f"• {lbl}" for lbl in enabled)
    return f"📦 *Dịch vụ đang bật:*\n{body}\n\nBấm ⚙️ để tự cấu hình:"


# ---------------- Panel cấu hình (thuần theo prefs) ----------------

def _time_rows(selected: list[str], ns: str) -> list[list[InlineKeyboardButton]]:
    """Lưới nút giờ preset (toggle). ns = tiền tố callback, vd 'menu:cfg:gold:time'."""
    rows, row = [], []
    for hhmm in TIME_PRESETS:
        disp = hhmm_to_display(hhmm)
        on = disp in selected
        row.append(InlineKeyboardButton(("✅ " if on else "") + disp, callback_data=f"{ns}:{hhmm}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return rows


def gold_panel(times: list[str]) -> tuple[str, InlineKeyboardMarkup]:
    cur = ", ".join(times) if times else "theo hệ thống"
    text = f"🥇 *Cấu hình Giá vàng*\nGiờ nhận: *{cur}*\n_Bấm để bật/tắt giờ (trống = theo hệ thống)._"
    rows = _time_rows(times, "menu:cfg:gold:time")
    rows.append([InlineKeyboardButton("◀️ Quay lại", callback_data="menu:mine")])
    return text, InlineKeyboardMarkup(rows)


def crypto_panel(prefs: dict) -> tuple[str, InlineKeyboardMarkup]:
    mode = prefs.get("mode", "system")
    times = prefs.get("times", [])
    coins = prefs.get("coins", [])
    text = (
        "📈 *Cấu hình Crypto*\n"
        f"Chế độ: *{ {'system':'Theo hệ thống','custom':'Tùy chỉnh','off':'Tắt'}.get(mode, mode) }*\n"
        f"Giờ: *{', '.join(times) or '—'}*  ·  Đồng: *{', '.join(coins) or 'tất cả'}*"
    )
    rows = [[
        InlineKeyboardButton(("✅ " if mode == m else "") + lbl, callback_data=f"menu:cfg:crypto:mode:{m}")
        for m, lbl in [("system", "Theo HT"), ("custom", "Tùy chỉnh"), ("off", "Tắt")]
    ]]
    rows += _time_rows(times, "menu:cfg:crypto:time")
    crow = []
    for sym in CRYPTO_SYMBOLS:
        crow.append(InlineKeyboardButton(("✅ " if sym in coins else "") + sym, callback_data=f"menu:cfg:crypto:coin:{sym}"))
        if len(crow) == 4:
            rows.append(crow); crow = []
    if crow:
        rows.append(crow)
    rows.append([InlineKeyboardButton("◀️ Quay lại", callback_data="menu:mine")])
    return text, InlineKeyboardMarkup(rows)


def news_panel(cats: list[str]) -> tuple[str, InlineKeyboardMarkup]:
    text = "📰 *Cấu hình Tin tức*\n_Chọn loại tin (không chọn = tất cả)._"
    rows, row = [], []
    for c in NEWS_CATEGORIES:
        on = c["key"] in cats
        row.append(InlineKeyboardButton(("✅ " if on else "") + c["label"], callback_data=f"menu:cfg:news:cat:{c['key']}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Quay lại", callback_data="menu:mine")])
    return text, InlineKeyboardMarkup(rows)


def football_panel(prefs: dict) -> tuple[str, InlineKeyboardMarkup]:
    times = prefs.get("times", [])
    teams = prefs.get("teams", [])
    text = (
        "⚽ *Cấu hình Bóng đá*\n"
        f"Giờ: *{', '.join(times) or 'theo hệ thống'}*\n"
        f"Đội yêu thích: *{', '.join(teams) or 'tất cả'}*"
    )
    rows = _time_rows(times, "menu:cfg:football:time")
    rows.append([InlineKeyboardButton("⭐ Sửa đội yêu thích", callback_data="menu:cfg:football:teams")])
    rows.append([InlineKeyboardButton("◀️ Quay lại", callback_data="menu:mine")])
    return text, InlineKeyboardMarkup(rows)


# ---------------- Truy xuất DB + render ----------------

async def _cfg_view(session, user_id: int, module: str) -> tuple[str, InlineKeyboardMarkup]:
    if module == "gold":
        return gold_panel(await settings_service.get_gold_times(session, user_id))
    if module == "crypto":
        return crypto_panel(await settings_service.get_crypto_prefs(session, user_id))
    if module == "news":
        return news_panel(await settings_service.get_news_categories(session, user_id))
    if module == "football":
        return football_panel(await settings_service.get_football_prefs(session, user_id))
    return "❓ Không có cấu hình.", build_main_menu()


async def _mine_view(session, user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    modules = await subscription_service.list_modules(session, user_id)
    text = format_owned(modules)
    rows = [
        [InlineKeyboardButton(f"⚙️ {MODULE_LABELS[k]}", callback_data=f"menu:cfg:{k}")]
        for k in CONFIGURABLE if modules.get(k)
    ]
    rows.append([InlineKeyboardButton("◀️ Quay lại", callback_data="menu:home")])
    return text, InlineKeyboardMarkup(rows)


# ---------------- Handlers ----------------

@require_active
async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧭 *Menu chính* — chọn mục:", parse_mode=ParseMode.MARKDOWN, reply_markup=build_main_menu()
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    tg = update.effective_user
    user, _ = await get_or_create_user(tg.id, tg.username, tg.full_name)
    if user.status == "banned" or not is_active(user):
        await query.answer("⛔ Tài khoản không hợp lệ hoặc đã hết hạn.", show_alert=True)
        return
    await query.answer()
    data = query.data
    parts = data.split(":")

    async def edit(text, markup):
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)

    try:
        if data == "menu:home":
            await edit("🧭 *Menu chính* — chọn mục:", build_main_menu())
        elif data == "menu:buy":
            await edit("🛒 *Mua gói* — chọn kiểu:", build_buy_root())
        elif data == "menu:buy:pkg":
            await edit("🎯 *Gói combo / Full* (hạn 30 ngày):", build_products_kb("pkg"))
        elif data == "menu:buy:single":
            await edit("🧩 *Mua lẻ dịch vụ* (hạn 30 ngày):", build_products_kb("single"))
        elif data == "menu:help":
            await edit(
                "ℹ️ Dùng 🛒 Mua gói để đăng ký; 📦 Gói đã mua để tự cấu hình dịch vụ.",
                build_main_menu(),
            )
        elif data == "menu:mine":
            async with AsyncSessionLocal() as s:
                text, markup = await _mine_view(s, user.id)
            await edit(text, markup)
        elif parts[:2] == ["menu", "cfg"]:
            await _handle_cfg(query, context, user.id, parts[2:], edit)
    except Exception:  # noqa: BLE001 — callback lỗi thì bỏ qua để không kẹt UI
        return


async def _handle_cfg(query, context, user_id: int, rest: list[str], edit) -> None:
    module = rest[0]
    async with AsyncSessionLocal() as s:
        if len(rest) == 1:  # mở panel
            text, markup = await _cfg_view(s, user_id, module)
            await edit(text, markup)
            return

        action = rest[1]
        if module == "gold" and action == "time":
            times = await settings_service.get_gold_times(s, user_id)
            await settings_service.set_gold_times(s, user_id, toggle(times, hhmm_to_display(rest[2])))
        elif module == "crypto":
            prefs = await settings_service.get_crypto_prefs(s, user_id)
            if action == "mode":
                prefs["mode"] = rest[2]
            elif action == "time":
                prefs["times"] = toggle(prefs["times"], hhmm_to_display(rest[2]))
            elif action == "coin":
                prefs["coins"] = toggle(prefs["coins"], rest[2])
            await settings_service.set_crypto_prefs(s, user_id, prefs["mode"], prefs["times"], prefs["coins"])
        elif module == "news" and action == "cat":
            cats = await settings_service.get_news_categories(s, user_id)
            await settings_service.set_news_categories(s, user_id, toggle(cats, rest[2]))
        elif module == "football" and action == "time":
            prefs = await settings_service.get_football_prefs(s, user_id)
            await settings_service.set_football_prefs(
                s, user_id, toggle(prefs["times"], hhmm_to_display(rest[2])), prefs["teams"]
            )
        elif module == "football" and action == "teams":
            context.user_data["menu_await"] = "football_teams"
            await edit(
                "⭐ Gõ tên đội yêu thích, cách nhau dấu phẩy (vd `Arsenal, Real Madrid`). "
                "Gửi `xoa` để bỏ hết.",
                InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Quay lại", callback_data="menu:cfg:football")]]),
            )
            return
        await s.commit()
        text, markup = await _cfg_view(s, user_id, module)
    await edit(text, markup)


async def menu_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Nhận đội yêu thích khi đang chờ (group=1). Không chờ → im lặng."""
    if context.user_data.get("menu_await") != "football_teams":
        return
    context.user_data.pop("menu_await", None)
    raw = (update.message.text or "").strip()
    teams = [] if raw.lower() == "xoa" else [t.strip() for t in raw.split(",") if t.strip()]
    tg = update.effective_user
    user, _ = await get_or_create_user(tg.id, tg.username, tg.full_name)
    async with AsyncSessionLocal() as s:
        prefs = await settings_service.get_football_prefs(s, user.id)
        await settings_service.set_football_prefs(s, user.id, prefs["times"], teams)
        await s.commit()
    await update.message.reply_text(
        f"✅ Đội yêu thích: *{', '.join(teams) or '(tất cả)'}*.  Mở /menu để tiếp tục.",
        parse_mode=ParseMode.MARKDOWN,
    )
