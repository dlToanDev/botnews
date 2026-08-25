# 🗂️ Kế hoạch Thực thi Theo Phase

Tài liệu này chia dự án thành **4 Phase tuần tự**. Mỗi phase là một file riêng, gồm:
- **Mục tiêu** & kết quả bàn giao (Deliverable)
- **Danh sách task** theo thứ tự thực hiện (làm từ trên xuống)
- **Definition of Done (DoD)** — tiêu chí nghiệm thu để coi là xong
- **Phụ thuộc** — cần hoàn thành gì trước

## Tiến độ tổng thể

| Phase | Nội dung | Thời lượng | Trạng thái |
|-------|----------|-----------|-----------|
| [Phase 0](phase-0-setup.md) | Chuẩn bị môi trường & khung dự án | 1–2 ngày | ✅ **Hoàn thành** |
| [Phase 1](phase-1-core-bot.md) | Core Bot + Lịch cá nhân | Tuần 1–2 | ✅ **Hoàn thành** (chờ token để chạy bot live) |
| [Phase 2](phase-2-web-admin.md) | Web Admin + Phân quyền SaaS | Tuần 3–4 | ✅ **Hoàn thành** |
| [Phase 3](phase-3-integrations.md) | Real-time Integrations (4 module) | Tuần 5–7 | ⬜ Chưa bắt đầu |
| [Phase 4](phase-4-deployment.md) | Deployment VPS + Bảo mật + Backup | Tuần 8 | ⬜ Chưa bắt đầu |

## Nguyên tắc thực thi
1. **Không nhảy phase.** Mỗi phase phụ thuộc kết quả phase trước.
2. **Hoàn thành DoD trước khi qua phase mới.** DoD chính là điểm kiểm tra chất lượng.
3. **Commit theo task.** Mỗi task xong → 1 commit rõ ràng.
4. Tham chiếu chi tiết kiến trúc & code mẫu tại [`../../IMPLEMENTATION_ROADMAP.md`](../../IMPLEMENTATION_ROADMAP.md).
