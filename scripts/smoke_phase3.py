"""Smoke test Phase 3 — adapters live + logic alert (patch gửi message)."""
import asyncio

TEST_TG = 777_000_111


async def main() -> int:
    from sqlalchemy import delete as sa_delete

    import app.worker.tasks.send_message as sm
    from app.core.database import AsyncSessionLocal
    from app.integrations import crypto, football, gold, news
    from app.models.user import User, UserSettings
    from app.repositories import module_repo, user_repo
    from app.services import settings_service, subscription_service, user_service
    from app.worker.tasks import crypto_alert, gold_alert, news_push

    failures: list[str] = []
    calls: list = []

    def check(name, cond):
        print(f"[{'OK ' if cond else 'ERR'}] {name}")
        if not cond:
            failures.append(name)

    # patch gửi message
    sm.send_message_task.delay = lambda chat_id, text: calls.append((chat_id, text))

    # 1) Adapters live
    btc = await crypto.get_price("BTCUSDT")
    check(f"Crypto live BTCUSDT (price={btc and btc['price']})", bool(btc and btc["price"] > 0))
    golds = await gold.get_gold_prices()
    check(f"Gold live ({len(golds)} sản phẩm)", len(golds) > 0)
    newsitems = await news.get_news()
    check(f"News RSS live ({len(newsitems)} tin)", len(newsitems) > 0)
    check("Football chưa cấu hình key → is_configured=False", football.is_configured() is False)

    # 2) Seed user + bật module + cấu hình
    async with AsyncSessionLocal() as s:
        await s.execute(sa_delete(User).where(User.telegram_id == TEST_TG))
        await s.commit()
    user, _ = await user_service.get_or_create_user(TEST_TG, "vip", "Khách VIP")
    async with AsyncSessionLocal() as s:
        for key in ("crypto", "gold", "news"):
            await subscription_service.set_module(s, user.id, key, True)
        await s.commit()
    await settings_service.add_crypto_watch(TEST_TG, "BTCUSDT", 0.001)
    await settings_service.set_news_keywords(TEST_TG, ["a", "và"])  # khớp nhiều tiêu đề VN
    async with AsyncSessionLocal() as s:
        st = (await s.execute(
            __import__("sqlalchemy").select(UserSettings).where(UserSettings.user_id == user.id)
        )).scalar_one()
        st.gold_alert_pct = 1  # Numeric(5,2): dùng 1% (0.001 sẽ bị làm tròn về 0.00)
        await s.commit()

    # 3) eligible_users
    async with AsyncSessionLocal() as s:
        elig = await module_repo.eligible_users(s, "crypto")
    check("eligible_users(crypto) gồm user test", any(u.id == user.id for u, _ in elig))

    # 4) Crypto alert: trigger + dedup
    calls.clear()
    n1 = await crypto_alert._run()
    n2 = await crypto_alert._run()  # dedup → 0
    check(f"Crypto alert gửi lần 1 ({n1}) > 0", n1 > 0)
    check(f"Crypto alert dedup lần 2 ({n2}) == 0", n2 == 0)

    # 5) Gold alert: ép baseline lệch để pct lớn
    from app.core.redis_client import redis_client
    sjc = await gold.get_gold_by_code("SJC")
    if sjc:
        await redis_client.set("gold:baseline:SJC", float(sjc["sell"]) * 0.5)  # pct ~ +100%
    calls.clear()
    ng = await gold_alert._run()
    check(f"Gold alert gửi ({ng}) > 0", ng > 0)

    # 6) News push: có tin khớp keyword
    calls.clear()
    nn = await news_push._run()
    check(f"News push gửi ({nn}) > 0", nn > 0)

    # cleanup
    async with AsyncSessionLocal() as s:
        await s.execute(sa_delete(User).where(User.telegram_id == TEST_TG))
        await s.commit()
    await redis_client.delete("gold:baseline:SJC")
    print("[i] Đã dọn dữ liệu test.")

    print("\n=>", "TẤT CẢ OK ✅" if not failures else f"CÓ LỖI ❌ ({failures})")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
