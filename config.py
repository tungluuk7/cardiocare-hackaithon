from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import os

load_dotenv()

# ── Múi giờ Việt Nam (UTC+7, không có DST) ──────────────────────────────────
# Server deploy (Render) chạy UTC. Nếu lấy giờ theo múi giờ máy chủ
# (datetime.now() "naive", hay SQLite datetime('now','localtime')) thì mọi mốc
# thời gian sẽ lệch 7 giờ so với Hà Nội. Vì vậy LUÔN tính mốc Hà Nội tất định.
VN_TZ = timezone(timedelta(hours=7))


def now_vn() -> datetime:
    """Thời điểm hiện tại theo giờ Hà Nội (UTC+7), độc lập múi giờ máy chủ."""
    return datetime.now(VN_TZ)


# Biểu thức SQLite cho "bây giờ" theo giờ Hà Nội. 'now' trong SQLite LUÔN là UTC,
# nên cộng 7 giờ = giờ Việt Nam bất kể OS của server.
SQLITE_NOW_VN = "datetime('now','+7 hours')"

class Settings:
    # VNPT SmartVoice — domain gốc, code tự ghép path (/tts-service/..., /stt-service/...)
    VNPT_VOICE_BASE_URL:    str = os.getenv("VNPT_VOICE_TTS_URL", "https://api.idg.vnpt.vn").rstrip("/")
    VNPT_VOICE_TTS_URL:     str = os.getenv("VNPT_VOICE_TTS_URL", "")
    VNPT_VOICE_TOKEN_ID:    str = os.getenv("VNPT_VOICE_TOKEN_ID", "")     # TTS token id
    VNPT_VOICE_TOKEN_KEY:   str = os.getenv("VNPT_VOICE_TOKEN_KEY", "")    # TTS token key
    VNPT_VOICE_STT_URL:     str = os.getenv("VNPT_VOICE_STT_URL", "")
    VNPT_VOICE_STT_TOKEN_ID:  str = os.getenv("VNPT_VOICE_STT_TOKEN_ID", "")   # STT token id
    VNPT_VOICE_STT_TOKEN_KEY: str = os.getenv("VNPT_VOICE_STT_TOKEN_KEY", "")  # STT token key
    # Access token (Bearer) — dùng chung cho cả TTS và STT
    VNPT_VOICE_ACCESS_TOKEN:  str = os.getenv("VNPT_VOICE_ACCESS_TOKEN", os.getenv("VNPT_ACCESS_TOKEN", ""))

    VNPT_BOT_URL: str = os.getenv("VNPT_BOT_URL", "")
    VNPT_ACCESS_TOKEN: str = os.getenv("VNPT_ACCESS_TOKEN", "")
    VNPT_TOKEN_ID: str = os.getenv("VNPT_TOKEN_ID", "")
    VNPT_TOKEN_KEY: str = os.getenv("VNPT_TOKEN_KEY", "")
    VNPT_BOT_ID: str = os.getenv("VNPT_BOT_ID", "")

    ALERT_EMAIL_FROM: str = os.getenv("ALERT_EMAIL_FROM", "")
    ALERT_EMAIL_TO: str = os.getenv("ALERT_EMAIL_TO", "")

    SMTP_HOST: str     = os.getenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
    SMTP_PORT: int     = int(os.getenv("SMTP_PORT", "2525"))
    SMTP_USER: str     = os.getenv("SMTP_USER", os.getenv("ALERT_EMAIL_FROM", ""))
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # Cho phép trỏ DB sang persistent disk khi deploy (Render mount /var/data).
    # Local/hackathon dùng file cạnh source như cũ.
    DB_PATH: str = os.getenv("DB_PATH", "cardiocare.db")

    USE_MOCK_AUDIO: bool = os.getenv("USE_MOCK_AUDIO", "false").lower() == "true"

    # ── Telephony (Twilio) — tự động gọi điện thật cho bệnh nhân ────────────────
    # .strip() để bỏ khoảng trắng thừa khi copy-paste vào .env
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN:  str = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "").strip()  # số trial Twilio cấp (+1...)
    # URL công khai (ngrok) để Twilio gọi webhook ghi âm về. Vd: https://abc.ngrok-free.app
    PUBLIC_BASE_URL:    str = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    # Bật/tắt bộ lập lịch tự động gọi theo giờ
    CALL_SCHEDULER_ENABLED: bool = os.getenv("CALL_SCHEDULER_ENABLED", "true").lower() == "true"

    # ── Zalo ZNS — gửi tin nhắn cho người thân khi RED (cần OA, để sau) ─────────
    # Access token OA lấy ở https://developers.zalo.me (OA Explorer / OAuth)
    ZALO_OA_ACCESS_TOKEN: str = os.getenv("ZALO_OA_ACCESS_TOKEN", "").strip()
    # Template ZNS đã được Zalo duyệt (chứa các tham số: ten_benh_nhan, trieu_chung, thoi_gian)
    ZALO_ZNS_TEMPLATE_ID: str = os.getenv("ZALO_ZNS_TEMPLATE_ID", "").strip()

    # ── Telegram Bot — kênh báo người thân KHẢ THI NGAY (miễn phí, không gate VN) ─
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()  # từ @BotFather
    TELEGRAM_CHAT_ID:   str = os.getenv("TELEGRAM_CHAT_ID", "").strip()    # chat_id người thân/điều dưỡng

settings = Settings()