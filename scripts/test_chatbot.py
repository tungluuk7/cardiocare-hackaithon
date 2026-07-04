"""
Test chatbot hỏi thăm CỤC BỘ — không cần server, không cần DB.

Chạy trong TERMINAL THẬT (PowerShell/CMD), KHÔNG chạy qua dấu '!':
    .venv\\Scripts\\python.exe test_chatbot.py

Gõ câu như bệnh nhân nói. Lệnh đặc biệt:
    reset  → bắt đầu phiên mới
    quit   → thoát
"""
import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()  # nạp .env để dùng Smartbot GenAI nếu đã cấu hình (không có thì tự fallback keyword)

import sys as _s, pathlib as _p
_s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))  # chạy được từ scripts/
from services.triage_engine import analyze, _classify
from services.chatbot_flow import generate_reply, get_opening_question
from services.symptom_schema import SYMPTOM_LABELS

ICON = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}


async def main():
    symptoms: list[str] = []
    turn = 0
    print("=" * 60)
    print("CardioCare — Chatbot hỏi thăm (test cục bộ)")
    print("Gõ 'reset' để làm lại, 'quit' để thoát.")
    print("=" * 60)
    print("\n🤖 BOT:", get_opening_question(0))

    while True:
        try:
            msg = input("\n🧓 BẠN (bệnh nhân): ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not msg:
            continue
        if msg.lower() in ("quit", "exit", "thoat"):
            break
        if msg.lower() == "reset":
            symptoms, turn = [], 0
            print("\n🤖 BOT:", get_opening_question(0))
            continue

        result = await analyze(msg)
        for s in result.symptoms:
            if s not in symptoms:
                symptoms.append(s)
        level = _classify(symptoms)
        reply = generate_reply(symptoms, level, turn)
        labels = [SYMPTOM_LABELS[s] for s in symptoms if s in SYMPTOM_LABELS]
        turn += 1

        print(f"   [{ICON.get(level, '')} {level} | tích luỹ: {', '.join(labels) or '—'}]")
        print("🤖 BOT:", reply)

    print("\nKết thúc phiên chat. Tạm biệt!")


if __name__ == "__main__":
    asyncio.run(main())
