# CardioCare

Hệ thống AI theo dõi hậu xuất viện 30 ngày cho **bệnh nhân tim mạch cao tuổi** sau
can thiệp mạch vành (PCI đặt stent). Tự động gọi điện hỏi thăm bằng giọng nói, trích
xuất triệu chứng, **phân luồng RED/YELLOW/GREEN**, và cảnh báo người thân/điều dưỡng
khi nguy cấp.

**Demo trực tuyến:** https://cardiocare-f2b2.onrender.com/static/index.html

---

## ⚡ Cài đặt & chạy — 1 lệnh

### Sử dụng Docker
```bash
docker compose up --build
```
Mở **http://localhost:8000/static/index.html** (dashboard đã có sẵn bệnh nhân demo).

## Tính năng chính
- **Voicebot tự động gọi** theo lịch (VNPT SmartVoice TTS/STT + Twilio) → hỏi thăm, ghi âm, chuyển văn bản.
- **Triage engine** phân luồng RED/YELLOW/GREEN theo quy tắc y khoa (Smartbot NER, fallback từ khoá).
- **Cảnh báo đa kênh** khi RED: Telegram/Zalo/SMS cho người thân + voicebot gọi lại bệnh nhân.
- **Chatbot** (văn bản + mic Web Speech tiếng Việt) cộng dồn triệu chứng qua nhiều lượt.
- **OCR giấy ra viện** (VNPT SmartReader) → tạo nhanh hồ sơ bệnh nhân (điều dưỡng duyệt).
- **Đo trải nghiệm (UX)**: VNPT SmartUX + lớp nội bộ (thời gian phản ứng ca RED…).

## Công nghệ
Python · FastAPI · SQLite · VNPT SmartVoice / SmartUX / SmartReader / Smartbot · Twilio · Telegram

## Cấu trúc
- `api/` — patients, calls, chatbot, telephony, ux, ocr
- `services/` — triage_engine, vnpt_voice, vnpt_ocr, smartbot_ner, alert, scheduler, …
- `static/` — dashboard, trang bệnh nhân, cửa sổ chat, báo cáo UX
- `main.py`, `config.py`, `database.py`, `seed_demo.py`
