"""
Telegram Bot — kênh báo người thân khi RED (miễn phí, không bị gate như SMS/Zalo VN).

  POST https://api.telegram.org/bot<TOKEN>/sendMessage
  Body: {"chat_id": ..., "text": ...}
  Response: {"ok": true, "result": {...}}

Lưu ý: bot chỉ nhắn được cho chat_id đã từng bấm /start bot (Telegram privacy).
Chưa cấu hình token/chat_id → CHẾ ĐỘ MÔ PHỎNG (chỉ log).

Hàm SYNC để dùng trực tiếp trong alert.send_alert.
"""
import httpx
from config import settings

API = "https://api.telegram.org"


def is_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)


def send_message(text: str, chat_id: str = "") -> dict:
    """Gửi 1 tin Telegram. Không raise — lỗi chỉ log."""
    target = chat_id or settings.TELEGRAM_CHAT_ID
    if not settings.TELEGRAM_BOT_TOKEN or not target:
        print(f"[telegram] (mô phỏng) gửi: {text[:90]}")
        return {"ok": False, "simulated": True}
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(
                f"{API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": target, "text": text},
            )
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        ok = bool(data.get("ok"))
        if not ok:
            print(f"[telegram] lỗi: status={r.status_code} resp={str(data)[:200]}")
        return {"ok": ok, "status": r.status_code, "response": data}
    except Exception as e:
        print(f"[telegram] exception: {e}")
        return {"ok": False, "error": str(e)}


def get_chat_ids() -> dict:
    """
    Helper lấy chat_id: sau khi bạn nhắn gì đó cho bot (vd /start), gọi hàm này
    để đọc các chat đã nhắn tới bot từ getUpdates.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"ok": False, "reason": "Chưa có TELEGRAM_BOT_TOKEN"}
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(f"{API}/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates")
        data = r.json()
        chats = []
        seen = set()
        for u in data.get("result", []):
            msg = u.get("message") or u.get("edited_message") or u.get("channel_post") or {}
            chat = msg.get("chat") or {}
            cid = chat.get("id")
            if cid and cid not in seen:
                seen.add(cid)
                chats.append({
                    "chat_id": cid,
                    "name": chat.get("first_name") or chat.get("title") or chat.get("username"),
                })
        return {"ok": True, "chats": chats}
    except Exception as e:
        return {"ok": False, "error": str(e)}
