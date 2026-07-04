# VNPT SmartUX — Hướng dẫn bật đo trải nghiệm người dùng (web)

CardioCare tích hợp **VNPT SmartUX** để thu thập & trực quan hoá tương tác người dùng
trên các trang web (dashboard điều dưỡng, chat, chi tiết bệnh nhân) — phục vụ tiêu chí
**"Trải nghiệm người dùng"** ở Vòng 2.

## Kiến trúc (2 lớp, bổ trợ nhau)

| Lớp | Đo gì | Trạng thái |
|---|---|---|
| **VNPT SmartUX** (`static/js/smartux.js`) | Pageview, click, scroll, **heatmap**, **userflow**, thiết bị/trình duyệt — TỰ ĐỘNG | Bật khi có `app_key` |
| **Lớp nội bộ** (`static/js/ux.js` → `/ux/events`) | Chỉ số nghiệp vụ SmartUX không tự suy ra, đặc biệt **thời gian phản ứng ca RED** (`red_acknowledged.wait_seconds`) | Luôn chạy (kể cả offline/demo) |

> Kênh **gọi điện** (giao diện chính của bệnh nhân) SmartUX không đo được — đo bằng
> dữ liệu backend (`call_logs`, `patients.last_answered_at`, `triage_results.confidence`).

## Bật SmartUX (3 bước)

1. **Đăng ký & tạo dự án:** truy cập <https://console-smartux.vnpt.vn/signup>, đăng ký,
   gửi thông tin cho team SmartUX để **active tài khoản**. Đăng nhập → **Tạo dự án mới**
   → chọn **Website**, nhập URL (vd URL Render/ngrok của CardioCare).
2. **Lấy app_key:** sau khi tạo, mở tab **Tích hợp** → copy `app_key` (và kiểm tra
   `VNPT.url` + đường dẫn `core-track.js` trong đoạn snippet console cấp).
3. **Cấu hình `.env`:**
   ```env
   SMARTUX_APP_KEY=<app_key_từ_console>
   SMARTUX_URL=https://smartux.icenter.ai
   SMARTUX_SDK_PATH=/sdk/web/core-track.js
   ```
   Khởi động lại server. Xong — SDK tự nạp vào `<head>` mọi trang.

Để **TRỐNG** `SMARTUX_APP_KEY` ⇒ SmartUX tắt, web vẫn chạy bình thường (chỉ dùng lớp nội bộ).

## Nghiệm thu (theo tài liệu VNPT)

- **Network:** mở DevTools → tab Network, lọc `console-smartux` / `core-track.js` → thấy
  request `200` là script đã chạy.
- **Console SmartUX:** vào dự án xem **Tổng quan** (số phiên, lượt xem trang, thiết bị…),
  **Heatmap** (điểm nóng click trên dashboard), **Luồng người dùng** (userflow).
- Nếu script chạy nhưng không lên số → liên hệ team SmartUX.

## Quyền riêng tư (cố ý)

`smartux.js` **KHÔNG** bật `track_forms` / `collect_from_forms` — hai lệnh này thu thập
nội dung ô nhập liệu, có thể dính mô tả triệu chứng của bệnh nhân. Quyết định này tuân thủ
cam kết bảo vệ dữ liệu cá nhân (Nghị định 356/2025/NĐ-CP) đã nêu trong hồ sơ.

## Xem báo cáo nội bộ (không cần SmartUX)

Mở `/(/)static/ux.html` — bảng chỉ số tổng hợp từ `/ux/report`, gồm ⭐ *thời gian phản ứng
ca RED trung bình*. Dùng để demo & chụp ảnh minh hoạ ngay cả khi chưa có `app_key`.
