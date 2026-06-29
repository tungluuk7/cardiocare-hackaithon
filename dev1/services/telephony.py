"""
Telephony adapter — gọi điện thật vào số bệnh nhân qua Twilio.

Luồng: Twilio quay số → phát câu hỏi (audio VNPT TTS qua /telephony/question.wav)
→ ghi âm câu trả lời → webhook /telephony/twilio-recording tải file về
→ VNPT STT → triage.

VNPT vẫn là lõi xử lý giọng nói; Twilio chỉ là "đường dây điện thoại".
"""
import asyncio
import httpx
from config import settings


def is_configured() -> bool:
    """Có đủ credentials Twilio + PUBLIC_BASE_URL để gọi thật không."""
    return bool(
        settings.PUBLIC_BASE_URL
        and settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_FROM_NUMBER
    )


def e164(number: str) -> str:
    """Chuẩn hoá số VN về E.164: 0975261207 → +84975261207."""
    n = (number or "").strip().replace(" ", "").replace("-", "")
    if n.startswith("+"):
        return n
    if n.startswith("0"):
        return "+84" + n[1:]
    if n.startswith("84"):
        return "+" + n
    return n


def _twiml(patient_id: int) -> str:
    base = settings.PUBLIC_BASE_URL
    action = f"{base}/telephony/twilio-recording?patient_id={patient_id}"
    return (
        "<Response>"
        f"<Play>{base}/telephony/question.wav</Play>"
        f'<Record maxLength="30" timeout="4" playBeep="true" '
        f'action="{action}" method="POST" />'
        "<Say>Cảm ơn bác. Tạm biệt bác.</Say>"
        "</Response>"
    )


async def call_patient(patient_id: int, to_number: str) -> dict:
    """Khởi tạo cuộc gọi ra qua Twilio. Trả {ok, status, body}."""
    if not is_configured():
        raise RuntimeError("Chưa cấu hình Twilio (thiếu credentials / PUBLIC_BASE_URL)")
    sid = settings.TWILIO_ACCOUNT_SID
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
    data = {
        "To":    e164(to_number),
        "From":  settings.TWILIO_FROM_NUMBER,
        "Twiml": _twiml(patient_id),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, data=data, auth=(sid, settings.TWILIO_AUTH_TOKEN))
    return {"ok": r.status_code in (200, 201), "status": r.status_code, "body": r.text[:600]}


def _twilio_creds_ready() -> bool:
    return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN
                and settings.TWILIO_FROM_NUMBER)


def send_sms(to_number: str, body: str) -> dict:
    """
    Gửi SMS qua Twilio (sync) — dùng báo người thân khi RED.
    Không cần PUBLIC_BASE_URL (SMS không có webhook). Chưa có creds → mô phỏng.
    """
    if not _twilio_creds_ready():
        print(f"[sms] (mô phỏng) SMS tới {e164(to_number)}: {body[:90]}")
        return {"ok": False, "simulated": True}
    sid = settings.TWILIO_ACCOUNT_SID
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        with httpx.Client(timeout=20) as client:
            r = client.post(
                url,
                data={"To": e164(to_number), "From": settings.TWILIO_FROM_NUMBER, "Body": body},
                auth=(sid, settings.TWILIO_AUTH_TOKEN),
            )
        ok = r.status_code in (200, 201)
        if not ok:
            print(f"[sms] Twilio lỗi: {r.status_code} {r.text[:200]}")
        return {"ok": ok, "status": r.status_code, "body": r.text[:300]}
    except Exception as e:
        print(f"[sms] exception: {e}")
        return {"ok": False, "error": str(e)}


async def download_recording(url: str) -> bytes:
    """Tải file ghi âm Twilio (Basic auth + đuôi .wav); retry vì file xử lý chậm."""
    wav_url = url if url.endswith((".wav", ".mp3")) else url + ".wav"
    auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        r = None
        for _ in range(6):
            r = await client.get(wav_url, auth=auth)
            if r.status_code == 200 and r.content:
                return r.content
            await asyncio.sleep(1.5)   # ghi âm có thể chưa sẵn sàng
        if r is not None:
            r.raise_for_status()
        return b""
