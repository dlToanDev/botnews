# Thiết kế: Báo kết quả bóng đá theo giờ (web config)

**Ngày:** 2026-08-29 · **Nhánh:** feat/web-admin-redesign

## Mục tiêu
Đến giờ cố định, báo kết quả vòng gần nhất của giải (chọn giải hoặc tất cả) qua
Telegram. Per-account: lọc theo đội yêu thích. Cấu hình trên web (tab Bóng đá).

## Nguồn
football_data.get_recent_results(code) → {matchday, matches[]}; match có
home/away/home_goals/away_goals. Giải: PL,PD,SA,BL1,FL1,CL. Cần FOOTBALL_DATA_KEY.

## Cấu hình
- Hệ thống: system_settings["football_notify"] = {enabled, times, leagues} (leagues rỗng=tất cả).
- Per-account: UserSettings.football_times (mới) + favorite_teams (đã có).

## Logic (football_service.py, thuần)
- filter_by_teams(matches, teams): teams rỗng → tất cả; có → giữ trận home/away chứa tên (lower).
- format_results_digest(sections, when): sections=[{label,matchday,matches}]; bỏ giải rỗng;
  header + mỗi giải 1 khối tỉ số monospace.
- Dùng gold_service.effective_times cho giờ.

## Worker football_digest (mỗi phút)
sys = get_football_notify; leagues hiệu lực = sys.leagues hoặc tất cả code. Với mỗi user
module football: times = effective_times(football_times, sys); khớp HH:MM → dedup →
fetch KQ từng giải (memo/run) → filter_by_teams theo favorite_teams → format → gửi.
Bỏ qua nếu football_data chưa cấu hình. Beat crontab(minute="*").

## Web
- Tab Bóng đá /settings: bật + giờ + tick giải. POST /settings/football.
- User card Bóng đá: giờ riêng + đội yêu thích (phẩy). POST /users/{id}/football.

## Model + constants
- UserSettings.football_times + migration.
- constants.FOOTBALL_LEAGUES [{code,label}] + FOOTBALL_LEAGUE_CODES.

## Kiểm thử
- Thuần: filter_by_teams, format_results_digest. Migration; smoke.

## Giữ nguyên
/epl…, /bxh, watchlist; Tin tức real-time.
