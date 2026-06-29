"""
Kiểm tra nhanh VNPT SmartVoice + pipeline triage trước khi demo.
Chạy:  .venv\\Scripts\\python test_vnpt.py
"""
import asyncio
from services.vnpt_voice import (
    text_to_speech, speech_to_text,
    _vnpt_tts_ready, _vnpt_stt_ready,
)
from services.triage_engine import analyze


async def main():
    print("=" * 50)
    print("KIEM TRA VNPT SMARTVOICE")
    print("=" * 50)
    print(f"TTS credentials: {'CO' if _vnpt_tts_ready() else 'THIEU'}")
    print(f"STT credentials: {'CO' if _vnpt_stt_ready() else 'THIEU'}")
    print("-" * 50)

    ok_tts = ok_stt = ok_triage = False

    # 1. TTS
    try:
        text = "Bác đau ngực dữ dội từ sáng, bị ngất một lần, giờ rất khó thở."
        audio = await text_to_speech(text)
        print(f"[1] TTS OK — sinh {len(audio):,} bytes audio")
        ok_tts = True
    except Exception as e:
        print(f"[1] TTS LOI: {e}")
        audio = None

    # 2. STT (nhận lại chính audio vừa sinh)
    if audio:
        try:
            transcript = await speech_to_text(audio, "test.wav")
            print(f"[2] STT OK — nhan dien: \"{transcript}\"")
            ok_stt = bool(transcript)
        except Exception as e:
            print(f"[2] STT LOI: {e}")
            transcript = ""
    else:
        transcript = text  # fallback dùng text gốc để test triage

    # 3. Triage
    try:
        r = await analyze(transcript)
        print(f"[3] Triage: {r.level} — {r.symptom_labels}")
        ok_triage = (r.level == "RED")
    except Exception as e:
        print(f"[3] Triage LOI: {e}")

    print("-" * 50)
    if ok_tts and ok_stt and ok_triage:
        print("KET QUA: TAT CA OK — san sang demo voi VNPT that")
    elif ok_triage:
        print("KET QUA: Triage OK. Voice co the dung fallback/mock — demo van chay.")
    else:
        print("KET QUA: Co loi — kiem tra .env va ket noi mang.")


if __name__ == "__main__":
    asyncio.run(main())
