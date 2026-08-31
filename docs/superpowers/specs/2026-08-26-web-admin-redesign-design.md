# Redesign Web Admin — Dashboard, Users, Gói dịch vụ

Ngày: 2026-08-26 · Nhánh: `feat/web-admin-redesign`

## Mục tiêu
Nâng cấp giao diện Web Admin (FastAPI + Jinja2 + HTMX + Tailwind CDN) theo hướng
**SaaS sáng, hiện đại**: dashboard đầy đủ có biểu đồ + bảng, trang Users dạng bảng
đẹp với nút thao tác, trang chi tiết user bố cục hợp lý, và **gán dịch vụ theo gói
định nghĩa sẵn** (bấm 1 nút bật cả bó module, vẫn tinh chỉnh từng module được).

Không đụng logic bot/Celery. Không thêm build step — chỉ thêm **Chart.js qua CDN**.

## Khái niệm quan trọng
- **Module dịch vụ** (5): `schedule`, `gold`, `crypto`, `football`, `news` — điều
  khiển tính năng thực tế của bot (bảng `subscription_modules`).
- **Gói dịch vụ (PACKAGES)** — MỚI: bó nhiều module có sẵn, định nghĩa trong
  `constants.py`. Bấm 1 nút "áp gói" → bật đúng bó module của gói đó.
- **`plan`** (`free`/`vip`) — chỉ là **nhãn hạng**, KHÔNG điều khiển module. Giữ
  nguyên, không trộn với gói dịch vụ.

## Gói mặc định (sửa được trong constants.py)
| key | Nhãn | Module |
|---|---|---|
| `full` | 🎯 Gói Full | tất cả 5 |
| `finance` | 💰 Gói Tài chính | gold, crypto |
| `sport` | ⚽ Gói Thể thao | football |
| `info` | 📰 Gói Thông tin | news, schedule |

## Thay đổi backend
1. `constants.py`: thêm `PACKAGES: list[dict]` (`key`, `label`, `modules`).
2. `user_repo.py`:
   - `count_new_by_month(session, months=6)` → dict {YYYY-MM: count} theo `created_at`.
   - `expiring_soon(session, days=7)` → list User sắp hết hạn (active, expires_at trong khoảng).
3. `subscription_service.py`: `apply_package(session, user_id, pkg_key)` — bật đúng
   bó module của gói (các module khác giữ nguyên), ghi log `package_apply`.
4. Router `subscriptions.py`: `POST /users/{id}/packages/{pkg}/apply` → redirect về detail.
5. Router `dashboard.py`: truyền thêm dữ liệu biểu đồ (status/module/plan/growth) + bảng sắp hết hạn.

## Thay đổi frontend
- `base.html`: sidebar/topbar chau chuốt, thêm mục nav "Gói", nạp Chart.js; macro
  Jinja dùng chung cho **badge trạng thái** và **nút**.
- `dashboard.html`: 4 KPI card, biểu đồ tròn (status), cột (module), đường (growth),
  bảng "Sắp hết hạn".
- `users.html`: bảng đẹp (avatar chữ, badge trạng thái/gói, chấm module), nút thao
  tác dạng icon, filter theo trạng thái + tìm kiếm.
- `user_detail.html`: header gọn, 2 cột cân đối; khối "Gói dịch vụ" (nút áp gói) +
  toggle từng module (giữ HTMX partial `_module_row.html`), nút đẹp có icon/xác nhận.

## Testing / verify
- Import biên dịch sạch (`python -c import app.web.main`).
- Chạy app, mở `/`, `/users`, `/users/{id}` không lỗi.
- 2 query repo mới có test đơn giản nếu khả thi.
