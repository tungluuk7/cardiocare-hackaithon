/*
 * ux.js — Lớp trừu tượng thu thập trải nghiệm người dùng (UX Analytics).
 *
 * Frontend chỉ gọi:  UX.track('event_name', { ...props });
 * Bên trong tự quyết định gửi đi đâu:
 *   1) VNPT SmartUX SDK   → khi window.SMARTUX_ENABLED = true (BTC cấp key)
 *   2) Fallback nội bộ    → POST /ux/events (luôn có, để demo & lấy số liệu)
 *
 * ⇒ Khi tích hợp SmartUX thật, CHỈ sửa hàm _sendSmartUX() bên dưới,
 *   KHÔNG phải đụng vào giao diện. Tên event giữ nguyên nên UX Metrics không đổi.
 *
 * Phạm vi: chỉ đo KÊNH WEB (dashboard, chat). Kênh gọi điện đo bằng backend.
 */
(function (global) {
    'use strict';

    // Session ẩn danh, sống trong 1 phiên trình duyệt — không chứa thông tin cá nhân.
    function sessionId() {
        try {
            var k = 'cc_ux_sid';
            var v = sessionStorage.getItem(k);
            if (!v) {
                v = 'sid-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
                sessionStorage.setItem(k, v);
            }
            return v;
        } catch (e) {
            return 'sid-nostore';
        }
    }

    // (1) Nhánh SmartUX — đẩy sự kiện NGHIỆP VỤ tuỳ biến vào SDK VNPT SmartUX.
    // SmartUX tự thu thập click/pageview/heatmap (xem smartux.js); riêng các chỉ số
    // đặc thù như 'red_acknowledged' + wait_seconds thì đẩy dưới dạng custom event
    // qua hàng đợi lệnh VNPT.q (mẫu add_event kiểu Countly mà SDK kế thừa).
    function _sendSmartUX(event, props) {
        try {
            if (global.VNPT && global.VNPT.q) {
                global.VNPT.q.push(['add_event', {
                    key: event,
                    count: 1,
                    segmentation: props || {}
                }]);
                return true;
            }
        } catch (e) { /* SDK chưa sẵn sàng — fallback nội bộ vẫn ghi */ }
        return false;
    }

    // (2) Fallback nội bộ — POST /ux/events. Dùng sendBeacon nếu có (không chặn UI).
    function _sendInternal(payload) {
        var body = JSON.stringify(payload);
        try {
            if (navigator.sendBeacon) {
                var blob = new Blob([body], { type: 'application/json' });
                if (navigator.sendBeacon('/ux/events', blob)) return;
            }
        } catch (e) { /* rơi xuống fetch */ }
        // fetch keepalive để không mất event khi rời trang
        fetch('/ux/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body,
            keepalive: true
        }).catch(function () { /* nuốt lỗi — analytics không được làm hỏng app */ });
    }

    var UX = {
        track: function (event, props) {
            props = props || {};
            var payload = {
                event: event,
                props: props,
                session_id: sessionId(),
                page: (global.location && global.location.pathname) || ''
            };
            // Ưu tiên SmartUX; luôn ghi nội bộ để có số liệu tổng hợp cho báo cáo.
            _sendSmartUX(event, props);
            _sendInternal(payload);
        }
    };

    global.UX = UX;
})(window);
