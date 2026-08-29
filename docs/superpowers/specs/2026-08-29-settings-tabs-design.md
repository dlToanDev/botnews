# Thiết kế: Trang Cấu hình dạng tab theo mục + cấu hình Tin tức hệ thống

**Ngày:** 2026-08-29 · **Nhánh:** feat/web-admin-redesign

## Mục tiêu
Gom trang /settings thành các mục (tab dọc trái): Vàng, Crypto, Tin tức, Bóng đá, AI.
Thêm cấu hình hệ thống cho Tin tức (danh mục mặc định).

## Bố cục
settings.html: cột trái list mục; phải là panel tương ứng. Chuyển tab bằng JS nhỏ.
Sau khi lưu, redirect kèm `?tab=<key>` để mở lại đúng tab.

## Nội dung
- Vàng / Crypto: giữ form hiện có.
- Tin tức (mới): 8 ô tick danh mục MẶC ĐỊNH hệ thống. Áp cho user chưa tự chọn.
  Lưu `system_settings["news_default"] = {"categories":[...]}`.
- Bóng đá / AI: panel khung, "Chưa có cấu hình hệ thống."

## Kỹ thuật
- `system_settings_service`: `get_news_default` / `set_news_default`.
- `settings.py`: GET nạp news_default; POST `/settings/news`; các POST redirect `?tab=`.
- `news_push.effective_news_cats(user_cats, default_cats)` (thuần): user nếu có,
  không thì default; cả hai trống → [] (nghĩa là tất cả ở `_passes_filter`).
  Worker dùng danh mục hiệu lực này thay cho user_cats trực tiếp.

## Kiểm thử
- Thuần: effective_news_cats (3 nhánh).
- Smoke: /settings đủ tab; lưu news_default; news_push lọc đúng.

## Ngoài phạm vi
Cấu hình hệ thống cho Bóng đá/AI (chỉ khung).
