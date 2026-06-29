"""
VNPT Smartbot client — gọi API hội thoại để hỗ trợ nhận diện triệu chứng.

Lưu ý: đây là Chatbot API (không phải NER thuần), response trả về text hội thoại
trong object.sb.card_data[*].text, KHÔNG có trường "entities" riêng.

QUAN TRỌNG — response là STREAMING (SSE), KHÔNG phải 1 JSON object:
  body gồm nhiều dòng dạng `data:{...json...}` (mỗi event 1 dòng). Vì vậy
  KHÔNG dùng response.json() được — phải tách từng dòng `data:` rồi json.loads.
  card_data_info.status: 0 = bản tin cuối (không stream) · 1 = đang stream
  (chưa xong) · 2 = bản tin cuối (có stream). Ta gộp text của mọi event.

Cách hoạt động:
  1. Gửi transcript bệnh nhân lên Smartbot
  2. Tách các event SSE, gộp text reply từ card_data
  3. Chạy keyword matching trên text đó để tìm triệu chứng
  4. Nếu không tìm thấy trong reply → chạy lại trên transcript gốc
  5. Nếu API lỗi / chưa có key → triage_engine tự fallback về keyword matching
"""

import json
import os
from typing import List

import httpx

import re

from services.symptom_schema import ALL_SYMPTOMS, match_symptoms

# Map mọi cách gọi (tên chuẩn + từ khoá) → tên triệu chứng chuẩn, để chuẩn hoá
# output GenAI về đúng tên mà rule engine hiểu.
_CANON = {}
for _s in ALL_SYMPTOMS:
    _CANON[_s.name.lower()] = _s.name
    for _kw in _s.keywords:
        _CANON[_kw.lower()] = _s.name

# ── Đọc credentials từ .env ───────────────────────────────────────────────────
SMARTBOT_API_URL      = os.getenv("SMARTBOT_API_URL", "https://assistant-stream.vnpt.vn/v1/conversation")
SMARTBOT_ACCESS_TOKEN = os.getenv("SMARTBOT_ACCESS_TOKEN", "")
SMARTBOT_TOKEN_ID     = os.getenv("SMARTBOT_TOKEN_ID", "")
SMARTBOT_TOKEN_KEY    = os.getenv("SMARTBOT_TOKEN_KEY", "")
SMARTBOT_BOT_ID       = os.getenv("SMARTBOT_BOT_ID", "")

# System prompt gửi qua API — phải BẬT "tính năng truyền prompt trong API" trên
# platform thì prompt này mới có hiệu lực. Để giống hệt prompt đã dán trên platform.
# Ép bot trả JSON để parser đọc chắc chắn (xem _parse_genai_symptoms).
SYSTEM_PROMPT = (
    "Bạn là trợ lý sàng lọc y tế CardioCare cho bệnh nhân tim mạch cao tuổi.\n"
    "Nhiệm vụ: đọc câu mô tả của bệnh nhân, trích xuất các triệu chứng họ ĐANG GẶP.\n"
    'Bỏ qua triệu chứng đã bị phủ định (vd "không đau ngực" thì KHÔNG tính đau ngực).\n'
    "CHỈ trả về đúng JSON sau, KHÔNG thêm lời dẫn, KHÔNG markdown:\n"
    '{"symptoms": ["<tên>", ...]}\n'
    "Tên triệu chứng phải nằm trong danh sách chuẩn: đau ngực, ngất, "
    "chảy máu vết thương, khó thở, chóng mặt, phù chân, hồi hộp, sốt.\n"
    'Nếu không có triệu chứng nguy hiểm, trả về {"symptoms": []}.'
)


def _bearer(token: str) -> str:
    """
    Chuẩn hoá Authorization header.
    Tránh lỗi double 'Bearer' khi giá trị trong .env đã có sẵn tiền tố 'Bearer '.
    """
    token = (token or "").strip()
    if token.lower().startswith("bearer "):
        token = token[len("bearer "):].strip()
    return f"Bearer {token}"


def _auth_headers(access_token: str, token_id: str, token_key: str) -> dict:
    return {
        "Authorization": _bearer(access_token),
        "Token-id":      token_id,
        "Token-key":     token_key,
        "Content-Type":  "application/json",
        "Accept":        "text/event-stream",  # endpoint trả streaming (SSE)
    }


# ── Entry point (gọi từ triage_engine) ───────────────────────────────────────

async def extract_symptoms_ner(
    transcript: str,
    sender_id: str = "cardiocare-patient",
    session_id: str = "session-default",
) -> List[str]:
    """
    Gửi transcript lên Smartbot, phân tích response → trả list tên triệu chứng.
    Raise exception nếu chưa có key hoặc lỗi mạng → triage_engine fallback.
    """
    if not SMARTBOT_ACCESS_TOKEN or not SMARTBOT_BOT_ID:
        raise ValueError("Chưa cấu hình SMARTBOT trong .env")
    if not SMARTBOT_TOKEN_ID or not SMARTBOT_TOKEN_KEY:
        raise ValueError("Thiếu SMARTBOT_TOKEN_ID hoặc SMARTBOT_TOKEN_KEY trong .env")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            SMARTBOT_API_URL,
            headers=_auth_headers(SMARTBOT_ACCESS_TOKEN, SMARTBOT_TOKEN_ID, SMARTBOT_TOKEN_KEY),
            json={
                "sender_id":     sender_id,
                "text":          transcript,
                "input_channel": "api",
                "metadata":      {},
                "session_id":    session_id,
                "bot_id":        SMARTBOT_BOT_ID,
                "settings": {
                    "system_prompt":  SYSTEM_PROMPT,
                    "advance_prompt": "null",
                },
            },
        )
        response.raise_for_status()
        raw = response.text

    return _parse_ner_response(raw, transcript)


# ── Parser response thật từ Smartbot (định dạng streaming SSE) ────────────────

def _iter_sse_events(raw: str) -> List[dict]:
    """
    Tách body SSE thành list các JSON object.
    Mỗi event là 1 dòng `data:{...}` (có thể nhiều event do streaming).
    Bỏ qua dòng rỗng, '[DONE]', và dòng không parse được.
    """
    events: List[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            line = line[len("data:"):].strip()
        if not line or line == "[DONE]":
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _card_text(event: dict) -> str:
    """Gộp text các card type text/quickreply trong 1 event."""
    try:
        card_data = event["object"]["sb"]["card_data"]
    except (KeyError, TypeError):
        return ""
    return " ".join(
        item.get("text", "")
        for item in card_data
        if isinstance(item, dict) and item.get("type") in ("text", "quickreply")
    )


def _parse_genai_symptoms(bot_text: str) -> "List[str] | None":
    """
    Nếu bot (GenAI) trả JSON {"symptoms": [...]} → đọc list, map về tên chuẩn.
    Trả None nếu không tìm thấy/parse được JSON (để caller fallback keyword matching).
    """
    match = re.search(r'\{.*?"symptoms".*?\}', bot_text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        raw_list = data["symptoms"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

    found: List[str] = []
    for item in raw_list:
        canon = _CANON.get(str(item).strip().lower())
        if canon and canon not in found:
            found.append(canon)
    return found


def _parse_ner_response(raw_response: str, original_transcript: str = "") -> List[str]:
    """
    Trích xuất triệu chứng từ response streaming của Smartbot.

    1. Tách các event SSE (`data:{...}`), gộp text reply của bot
    2. Nếu bot trả JSON GenAI {"symptoms": [...]} → dùng luôn (chính xác nhất)
    3. Nếu không → keyword matching trên text reply
    4. Nếu vẫn rỗng (vd bot fallback) → match transcript gốc (an toàn nhất)
    """
    events = _iter_sse_events(raw_response)
    bot_text = " ".join(_card_text(ev) for ev in events).strip()

    if bot_text:
        genai = _parse_genai_symptoms(bot_text)
        if genai:                      # GenAI trả JSON CÓ triệu chứng → tin GenAI
            return genai
        if genai is None:              # reply không phải JSON → keyword trên reply
            found = match_symptoms(bot_text)
            if found:
                return found
        # genai == [] (bot nói "không có triệu chứng") → vẫn double-check transcript
        # bên dưới để tránh bỏ sót RED (an toàn lâm sàng).

    return match_symptoms(original_transcript) if original_transcript else []


# ── Hàm test nhanh: python services/smartbot_ner.py ──────────────────────────

async def _test_api():
    """
    Gọi thử API với câu test, in ra response thật để kiểm tra format.
    Chạy: python -m services.smartbot_ner
    (Cần điền key vào .env trước)
    """
    # Đọc lại env sau khi load_dotenv() ở __main__
    access_token = os.getenv("SMARTBOT_ACCESS_TOKEN", "")
    token_id     = os.getenv("SMARTBOT_TOKEN_ID", "")
    token_key    = os.getenv("SMARTBOT_TOKEN_KEY", "")
    bot_id       = os.getenv("SMARTBOT_BOT_ID", "")
    api_url      = os.getenv("SMARTBOT_API_URL", "https://assistant-stream.vnpt.vn/v1/conversation")

    if not access_token:
        print("Chưa có SMARTBOT_ACCESS_TOKEN trong .env — không thể test API")
        return

    test_text = "đau ngực dữ dội từ sáng, hơi khó thở"
    print(f"Gửi lên Smartbot: '{test_text}'")
    print("-" * 50)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            api_url,
            headers=_auth_headers(access_token, token_id, token_key),
            json={
                "sender_id":     "test-001",
                "text":          test_text,
                "input_channel": "api",
                "metadata":      {},
                "session_id":    "test-session-001",
                "bot_id":        bot_id,
                "settings":      {"system_prompt": SYSTEM_PROMPT, "advance_prompt": "null"},
            },
        )

    print("HTTP Status:", response.status_code)
    raw = response.text
    print("Raw response (rút gọn 500 ký tự):")
    print(raw[:500])
    print("-" * 50)

    events = _iter_sse_events(raw)
    print(f"Số event SSE parse được: {len(events)}")
    for i, ev in enumerate(events):
        print(f"  event[{i}] card_text = {_card_text(ev)!r}")
    print("-" * 50)

    symptoms = _parse_ner_response(raw, test_text)
    print("Triệu chứng tìm được:", symptoms)


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()          # load file .env trước khi chạy
    asyncio.run(_test_api())
