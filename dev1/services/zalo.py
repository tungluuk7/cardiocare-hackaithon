"""
Zalo ZNS — gửi tin nhắn thông báo tới SĐT người thân khi phát hiện RED.

Dùng Zalo Notification Service (ZNS): gửi theo template đã duyệt tới số điện thoại
(không cần người nhận follow OA).

  POST https://business.openapi.zalo.me/message/template
  Header: access_token: <OA access token>
  Body:  {"phone": "84...", "template_id": "...", "template_data": {...}}
  Response: {"error": 0, "message": "Success", "data": {...}}   (error=0 là thành công)

Chưa cấu hình (thiếu access_token / template_id) → CHẾ ĐỘ MÔ PHỎNG: chỉ log nội
dung sẽ gửi, không gọi API. Hệ thống vẫn chạy bình thường.

Hàm SYNC để dùng trực tiếp trong alert.send_alert (cũng là sync).
"""
import httpx
from config import settings

ZNS_URL = "https://business.openapi.zalo.me/message/template"


def is_configured() -> bool:
    return bool(settings.ZALO_OA_ACCESS_TOKEN and settings.ZALO_ZNS_TEMPLATE_ID)


def _zalo_phone(number: str) -> str:
    """Chuẩn hoá số VN cho ZNS: 0975261207 → 84975261207 (không dấu +)."""
    n = (number or "").strip().replace(" ", "").replace("-", "").replace("+", "")
    if n.startswith("0"):
        return "84" + n[1:]
    if n.startswith("84"):
        return n
    return n


def send_zns(phone: str, template_data: dict, tracking_id: str = "") -> dict:
    """
    Gửi 1 tin ZNS. Trả {ok, simulated?, status?, response?}.
    Không raise — lỗi chỉ log, để không chặn luồng cảnh báo chính.
    """
    if not phone:
        return {"ok": False, "reason": "no_phone"}

    if not is_configured():
        print(f"[zalo] (mô phỏng) sẽ gửi ZNS tới {_zalo_phone(phone)}: {template_data}")
        return {"ok": False, "simulated": True}

    body = {
        "phone": _zalo_phone(phone),
        "template_id": settings.ZALO_ZNS_TEMPLATE_ID,
        "template_data": template_data,
    }
    if tracking_id:
        body["tracking_id"] = tracking_id

    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(
                ZNS_URL,
                json=body,
                headers={
                    "access_token": settings.ZALO_OA_ACCESS_TOKEN,
                    "Content-Type": "application/json",
                },
            )
        data = {}
        try:
            data = r.json()
        except Exception:
            pass
        ok = data.get("error") == 0
        if not ok:
            print(f"[zalo] ZNS lỗi: status={r.status_code} resp={str(data)[:200]}")
        return {"ok": ok, "status": r.status_code, "response": data}
    except Exception as e:
        print(f"[zalo] ZNS exception: {e}")
        return {"ok": False, "error": str(e)}
