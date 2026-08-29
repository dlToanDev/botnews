# Thiết kế: Menu phân cấp trong bot (mua gói + tự cấu hình)

**Ngày:** 2026-08-29 · **Nhánh:** feat/web-admin-redesign

## Mục tiêu
Lệnh /menu mở menu inline phân cấp:
- 🛒 Mua gói → theo Gói (Full/Combo) / Mua lẻ (Vàng, Crypto, Bóng đá, Tin tức, AI).
- 📦 Gói đã mua & Cài đặt → liệt kê dịch vụ đang bật; mỗi dịch vụ có nút ⚙️ Cấu hình
  để user TỰ setup (giống web): Vàng (giờ), Crypto (chế độ/giờ/đồng), Tin tức (danh mục),
  Bóng đá (giờ + đội yêu thích).

## Điều hướng (namespace `menu:`, sửa tin nhắn tại chỗ)
- menu:home, menu:buy, menu:buy:pkg, menu:buy:single, menu:mine
- menu:cfg:<module> → panel cấu hình
- Toggle: menu:cfg:gold:time:<HHMM>, crypto:mode:<m>|time:<HHMM>|coin:<SYM>,
  news:cat:<key>, football:time:<HHMM>, football:teams (nhập text)
- Nút sản phẩm dùng lại `buy:<key>` (buy_callback sẵn có → tạo đơn + QR).

## Nhập liệu
- Giờ: chọn từ preset (toggle) — tránh gõ text. TIME_PRESETS cố định.
- Đồng/danh mục: toggle nút.
- Đội bóng yêu thích: nhập text (handler group=1, cờ menu_await, không đụng calendar group 0).

## Hàm thuần (test được) — app/bot/handlers/menu.py
- toggle(lst, item); hhmm_to_display("0900")→"09:00".
- build_main_menu(), build_buy_root(), build_products_kb(ptype) (callback buy:/menu:).
- format_owned(modules_map) → text liệt kê dịch vụ bật.

## Handlers
- menu_cmd (@require_active) → menu chính.
- menu_callback (pattern ^menu:) → phân nhánh; toggle: đọc→sửa→lưu→re-render.
- menu_text_input (group=1) → nhận đội yêu thích khi menu_await set.
- main.py: CommandHandler("menu",...), CallbackQueryHandler(pattern ^menu:), thêm /menu vào BOT_COMMANDS.

## Kiểm thử
- Thuần: toggle, hhmm_to_display, build_products_kb (có buy:*), build_main_menu (menu:*),
  format_owned. Smoke: render các panel cfg cho 1 user.

## Ngoài phạm vi
Đổi reply-keyboard; cấu hình AI/schedule trong menu.
