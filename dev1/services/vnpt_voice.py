"""
Voice service: TTS + STT qua VNPT SmartVoice (api.idg.vnpt.vn).

Contract API (trích từ tài liệu VNPT SmartVoice):
  TTS  POST {base}/tts-service/v1/standard      → trả text_id (async)
       POST {base}/tts-service/v1/check-status  → poll lấy playlist[].audio_link
  STT  POST {base}/stt-service/v1/grpc/standard → trả object.results[0].alternatives[0].transcript

Cả 3 header BẮT BUỘC: Authorization (Bearer access_token), Token-id, Token-key.
TTS và STT có Token-id/Token-key KHÁC nhau, dùng chung Access token.

Fallback: gTTS (TTS) + SpeechRecognition (STT) khi VNPT không sẵn sàng.
"""
import io
import time
import uuid
import asyncio
import httpx
from config import settings

VOICEBOT_SCRIPT = (
    "Xin chào bác. Đây là hệ thống theo dõi sức khỏe của bệnh viện. "
    "Bác vừa xuất viện sau thủ thuật tim mạch. "
    "Bác có thể cho biết trong mấy ngày qua bác cảm thấy thế nào không? "
    "Bác có bị đau ngực, khó thở, chóng mặt, hoặc triệu chứng nào khó chịu không?"
)

# Câu hỏi ngắn dùng cho CUỘC GỌI ĐIỆN THOẠI (Twilio) — gọn, có cue "sau tiếng bíp"
PHONE_QUESTION = (
    "Xin chào bác. Đây là hệ thống chăm sóc sức khỏe của bệnh viện. "
    "Mấy ngày qua bác có bị đau ngực, khó thở, hay chóng mặt không ạ? "
    "Xin bác trả lời sau tiếng bíp."
)

_BASE = settings.VNPT_VOICE_BASE_URL  # https://api.idg.vnpt.vn


# ── Lời nhắn gọi lại bệnh nhân (callback) ─────────────────────────────────────

def build_callback_message(patient_name: str, level: str,
                           symptom_labels: list[str]) -> str:
    """Dựng nội dung lời nhắn thoại gọi lại, cá nhân hoá theo mức độ triage."""
    syms = ", ".join(symptom_labels) if symptom_labels else "một số dấu hiệu bất thường"
    if level == "RED":
        return (
            f"Xin chào bác {patient_name}. Đây là hệ thống chăm sóc sức khỏe của bệnh viện. "
            f"Chúng tôi ghi nhận bác đang có dấu hiệu: {syms}. "
            f"Đây là tình trạng cần được xử lý ngay. "
            f"Điều dưỡng sẽ gọi lại cho bác trong ít phút nữa. "
            f"Nếu bác thấy nặng hơn, xin hãy gọi ngay số một một năm, "
            f"hoặc nhờ người thân đưa bác tới bệnh viện gần nhất. "
            f"Bác giữ bình tĩnh và ngồi nghỉ bác nhé."
        )
    # YELLOW
    return (
        f"Xin chào bác {patient_name}. Đây là hệ thống chăm sóc sức khỏe của bệnh viện. "
        f"Chúng tôi ghi nhận bác có dấu hiệu: {syms}. "
        f"Bác nên nghỉ ngơi và theo dõi thêm. "
        f"Điều dưỡng sẽ sớm liên hệ để hỏi thăm tình hình của bác. "
        f"Cảm ơn bác đã sử dụng dịch vụ."
    )


# ── TTS ──────────────────────────────────────────────────────────────────────

async def text_to_speech(text: str, region: str = "female_north") -> bytes:
    """Text → audio bytes (WAV). Dùng VNPT nếu có credentials, fallback gTTS."""
    if _vnpt_tts_ready():
        try:
            return await _vnpt_tts(text, region)
        except Exception as e:
            print(f"[tts] VNPT lỗi: {e} — dùng gTTS")
    return _gtts_tts(text)


def _vnpt_tts_ready() -> bool:
    return bool(settings.VNPT_VOICE_TOKEN_ID and settings.VNPT_VOICE_ACCESS_TOKEN)


async def _vnpt_tts(text: str, region: str) -> bytes:
    headers = {
        "Content-Type":  "application/json",
        "Authorization": settings.VNPT_VOICE_ACCESS_TOKEN,
        "Token-id":      settings.VNPT_VOICE_TOKEN_ID,
        "Token-key":     settings.VNPT_VOICE_TOKEN_KEY,
    }
    payload = {
        "text":        text,
        "region":      region,     # female_north | female_central | female_south | male_*
        "speed":       "0.9",      # chậm hơn chút cho người già nghe rõ
        "text_split":  False,
        "audio_format": "wav",
        "sample_rate": 8000,       # 8000 = callbot (gọi điện thoại)
    }
    async with httpx.AsyncClient(timeout=60) as client:
        # B1: submit → nhận text_id
        r = await client.post(f"{_BASE}/tts-service/v1/standard", json=payload, headers=headers)
        r.raise_for_status()
        obj = r.json().get("object", {})
        link = _extract_audio_link(obj)
        text_id = obj.get("text_id")

        # B2: nếu chưa có link, poll check-status
        for _ in range(15):
            if link:
                break
            if not text_id:
                raise RuntimeError(f"TTS không trả text_id: {r.text[:200]}")
            await asyncio.sleep(1.2)
            cs = await client.post(
                f"{_BASE}/tts-service/v1/check-status",
                json={"text_id": text_id}, headers=headers,
            )
            cs.raise_for_status()
            link = _extract_audio_link(cs.json().get("object", {}))

        if not link:
            raise RuntimeError("TTS không lấy được audio_link sau khi poll")

        # B3: tải file audio về
        audio = await client.get(link)
        audio.raise_for_status()
        return audio.content


def _extract_audio_link(obj: dict) -> str | None:
    playlist = obj.get("playlist") or []
    if playlist and isinstance(playlist, list):
        return playlist[0].get("audio_link")
    return None


def _gtts_tts(text: str) -> bytes:
    """gTTS fallback — miễn phí, không cần API key."""
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text, lang="vi", slow=False).write_to_fp(buf)
    buf.seek(0)
    return buf.read()


# ── STT ──────────────────────────────────────────────────────────────────────

async def speech_to_text(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Audio bytes → transcript text. Dùng VNPT nếu có credentials, fallback Google STT."""
    if _vnpt_stt_ready():
        try:
            return await _vnpt_stt(audio_bytes, filename)
        except Exception as e:
            print(f"[stt] VNPT lỗi: {e} — dùng Google STT")
    return _google_stt(audio_bytes, filename)


def _vnpt_stt_ready() -> bool:
    return bool(settings.VNPT_VOICE_STT_TOKEN_ID and settings.VNPT_VOICE_ACCESS_TOKEN)


async def _vnpt_stt(audio_bytes: bytes, filename: str) -> str:
    headers = {
        "Authorization": settings.VNPT_VOICE_ACCESS_TOKEN,
        "Token-id":      settings.VNPT_VOICE_STT_TOKEN_ID,
        "Token-key":     settings.VNPT_VOICE_STT_TOKEN_KEY,
    }
    # mp3 cần báo convert_format; wav/pcm để mặc định
    is_mp3 = filename.lower().endswith(".mp3")
    mime = "audio/mpeg" if is_mp3 else "audio/wav"
    data = {"clientSession": str(uuid.uuid4())}
    if is_mp3:
        data["customConfiguration"] = '{"convert_format":"mp3"}'

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            f"{_BASE}/stt-service/v1/grpc/standard",
            files={"audioFile": (filename, audio_bytes, mime)},
            data=data,
            headers=headers,
        )
        r.raise_for_status()
        return _extract_transcript(r.json())


def _extract_transcript(data: dict) -> str:
    """object.results[*].alternatives[0].transcript → nối lại thành 1 chuỗi."""
    obj = data.get("object", {})
    results = obj.get("results") or []
    parts = []
    for res in results:
        alts = res.get("alternatives") or []
        if alts and alts[0].get("transcript"):
            parts.append(alts[0]["transcript"])
    return " ".join(parts).strip()


def _google_stt(audio_bytes: bytes, filename: str) -> str:
    """Google STT fallback qua thư viện SpeechRecognition — miễn phí."""
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language="vi-VN")
    except Exception as e:
        print(f"[stt] Google STT lỗi: {e}")
        return ""


# ── MOCK (test không cần audio) ───────────────────────────────────────────────

async def speech_to_text_mock(scenario: str = "yellow") -> str:
    scenarios = {
        "green":  "Bác cảm thấy bình thường, ăn uống được, đi lại nhẹ nhàng.",
        "yellow": "Bác hơi khó thở, đi lại thì mệt hơn bình thường, chân cũng hơi sưng.",
        "red":    "Bác đau ngực dữ dội từ sáng, ngất một lần, giờ đang rất khó thở.",
    }
    return scenarios.get(scenario, scenarios["green"])
