/*
 * smartux.js — Nạp SDK web VNPT SmartUX (đặt trong <head> mọi trang cần tracking).
 *
 * Theo "Tài liệu hướng dẫn tích hợp SDK Web VNPT SmartUX v1.0.0":
 *   - Đăng ký/đăng nhập https://console-smartux.vnpt.vn → tạo dự án Website → lấy app_key.
 *   - Snippet chuẩn dựng global VNPT.q rồi tải core-track.js; SDK tự động thu thập
 *     session / pageview / click / scroll / error / link, dựng heatmap & userflow.
 *
 * Ở đây app_key được lấy từ backend /ux/config (đọc từ .env: SMARTUX_APP_KEY),
 * KHÔNG nhúng cứng vào HTML — cùng cách quản lý secret với SmartVoice/Smartbot.
 * Khi chưa có app_key ⇒ bỏ qua hoàn toàn, trang chạy bình thường (không lỗi).
 *
 * CHỦ Ý QUYỀN RIÊNG TƯ: KHÔNG bật 'track_forms'/'collect_from_forms' vì chúng
 * thu thập nội dung ô nhập liệu — có thể dính mô tả triệu chứng của bệnh nhân.
 * Tuân thủ cam kết bảo vệ dữ liệu cá nhân (Nghị định 356/2025/NĐ-CP).
 */
(function () {
    'use strict';
    fetch('/ux/config')
        .then(function (r) { return r.json(); })
        .then(function (cfg) {
            if (!cfg || !cfg.enabled || !cfg.app_key) return;   // chưa cấu hình → thôi

            var VNPT = window.VNPT = window.VNPT || {};
            VNPT.q = VNPT.q || [];
            VNPT.app_key = cfg.app_key;
            VNPT.url = cfg.url;

            // Chỉ bật các phép đo hành vi ẩn danh — KHÔNG đụng nội dung form.
            ['track_sessions', 'track_pageview', 'track_clicks',
             'track_scrolls', 'track_errors', 'track_links'
            ].forEach(function (cmd) { VNPT.q.push([cmd]); });

            var s = document.createElement('script');
            s.type = 'text/javascript';
            s.async = true;
            s.src = cfg.url + cfg.sdk_path;
            s.onload = function () {
                if (typeof VNPT.init === 'function') VNPT.init();
                window.SMARTUX_READY = true;   // báo cho ux.js biết SDK đã sẵn sàng
            };
            (document.head || document.documentElement).appendChild(s);
        })
        .catch(function () { /* offline / chưa cấu hình — nuốt lỗi, không phá app */ });
})();
