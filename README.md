# CardioCare

Hệ thống AI theo dõi hậu xuất viện 30 ngày cho **bệnh nhân tim mạch cao tuổi** sau
can thiệp mạch vành (PCI đặt stent). Tự động gọi điện hỏi thăm bằng giọng nói, trích
xuất triệu chứng, **phân luồng RED/YELLOW/GREEN**, và cảnh báo người thân/điều dưỡng
khi nguy cấp.

**Demo trực tuyến:** https://cardiocare-f2b2.onrender.com/static/index.html

---

## ⚡ Cài đặt & chạy — 1 lệnh

### Cách 1 — Docker (khuyên dùng, không cần cài Python)
```bash
docker compose up --build
```
Mở **http://localhost:8000/static/index.html** (dashboard đã có sẵn bệnh nhân demo).

### Cách 2 — Chạy trực tiếp (cần Python 3.12+)
| Hệ điều hành | Lệnh |
|---|---|
| **Windows** (PowerShell) | `./run.ps1 -Seed` |
| **Linux / macOS** | `bash run.sh --seed` |

Cả hai tự tạo virtualenv, cài dependencies, seed dữ liệu mẫu và khởi động server.

> Không cần `.env` vẫn chạy được (chế độ fallback: giọng nói gTTS, triage theo từ khoá,
> gọi điện mô phỏng). Để bật đầy đủ VNPT SmartVoice/SmartUX/SmartReader, Twilio, Telegram…
> tạo file `.env` từ `.env.example` rồi điền khoá (xem `SMARTUX_SETUP.md`, `TWILIO_SETUP.md`).

Sau khi chạy:
- Dashboard điều dưỡng: http://localhost:8000/static/index.html
- Cửa sổ chat (bệnh nhân): http://localhost:8000/static/phone.html
- Báo cáo UX: http://localhost:8000/static/ux.html
- API docs: http://localhost:8000/docs

---

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
