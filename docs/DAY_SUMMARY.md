# CardioCare — Wrap-up công việc Dev 1

**Ngày:** 2026-06-29 · **Vai trò:** Dev 1 (Backend + VNPT Voice) · **Đối chiếu:** `cardiocare-tasks-1.html`

---

## A. Nhiệm vụ trong file task

### Dev 1 — Backend + VNPT Voice (3 ngày)

| Ngày | Task | Trạng thái |
|---|---|---|
| 1 | Tạo project, `requirements.txt`, `.env` | ✅ |
| 1 | `database.py` tạo bảng (patients, call_logs, triage_results) | ✅ (giờ có thêm `alerts`) |
| 1 | `api/patients.py` — POST/GET /patients | ✅ |
| 1 | VNPT key + `speech_to_text_mock()` trả đúng text | ✅ |
| 1 | `uvicorn` + /docs | ✅ |
| 2 | Import `analyze()` vào `calls.py` | ✅ |
| 2 | `POST /calls/simulate` (STT→triage→DB→alert) | ✅ |
| 2 | `GET /dashboard` sorted RED→YELLOW→GREEN | ✅ |
| 2 | Test e2e `scenario=yellow` | ✅ |
| 3 | Test audio thật upload | ✅ (vượt: cả cuộc gọi điện thật) |
| 3 | Fix bugs integration | ✅ |
| 3 | Deploy Railway/Render | ✅ Sẵn sàng — `Procfile`, `render.yaml`, `railway.json`, `runtime.txt`, `DEPLOY.md` (xem mục F) |
| 3 | `GET /patients/{id}/history` (optional) | ✅ Trả patient + toàn bộ call_logs/triage, mới nhất trước |

### Dev 1 — Chatbot Backend (`api/chatbot.py`) — 5/5 ✅

| Task | Trạng thái |
|---|---|
| `POST /chatbot/message` (NER+triage, cộng dồn triệu chứng) | ✅ |
| `POST /chatbot/transcribe` (audio → VNPT STT) | ✅ |
| `GET /chatbot/opening` | ✅ |
| `POST /chatbot/alert-patient` (fix gắn patient_id) | ✅ |
| `DELETE /chatbot/session/{id}` | ✅ |

---

## B. Làm thêm (ngoài file task)

| Tính năng | Mô tả | Trạng thái |
|---|---|---|
| Sửa lỗi VNPT 401 | Thiếu header `Authorization` → TTS/STT chạy thật `api.idg.vnpt.vn` | ✅ |
| Matcher triệu chứng nâng cao | Token-match + lọc từ đệm + phủ định (9/9 test) | ✅ |
| Voicebot gọi lại khi RED | Sinh lời nhắn VNPT TTS cá nhân hóa | ✅ |
| **Tự động gọi điện theo giờ** | Scheduler + Twilio → gọi THẬT, reo đúng giờ, STT→triage | ✅ |
| Tracking nhấc máy | `last_answered_at` chỉ set khi bệnh nhân trả lời | ✅ |
| **RED → báo người thân** | Telegram (chạy thật) + Zalo (sẵn) + SMS (fallback) | ✅ |
| Xóa bệnh nhân | `DELETE /patients/{id}` + nút 🗑 | ✅ |
| Dọn Stringee → Twilio | Gỡ sạch code thừa | ✅ |

---

## C. Ma trận cảnh báo

| Mức | Hành động |
|---|---|
| RED | Lưu DB + Telegram cho người thân (+ voicebot gọi lại bệnh nhân) |
| YELLOW | Chỉ lưu DB |
| GREEN | Không cảnh báo (không ghi DB) |

**Kênh báo người thân** (`alert.py::_notify_family`, ưu tiên): Zalo ZNS → **Telegram** (đang chạy) → SMS Twilio → mô phỏng.

---

## D. Luồng end-to-end đã chạy THẬT

```
📅 Đặt giờ hẹn → ⏰ scheduler (mỗi 30s) → 📞 Twilio quay số → máy reo
→ 🔊 câu hỏi VNPT TTS → 🎤 bệnh nhân trả lời → ghi âm
→ 📥 VNPT STT → 🚦 triage RED/YELLOW/GREEN
→ 🔔 cảnh báo dashboard + 📲 Telegram người thân (nếu RED) + 📞 voicebot gọi lại
```

---

## E. Kiến trúc & stack

**Stack:** Python + FastAPI + SQLite + VNPT SmartVoice (TTS/STT) + Twilio (telephony) + Telegram (cảnh báo người thân).

**File backend Dev 1:**
- `api/`: patients, calls, chatbot, telephony
- `services/`: vnpt_voice, triage_engine, smartbot_ner, symptom_schema, chatbot_flow, alert, pipeline, scheduler, telephony, zalo, telegram
- `database.py`, `config.py`, `main.py`, `static/index.html`

**Công cụ/tài liệu:** `run.ps1`, `setup_ngrok.ps1`, `seed_demo.py`, `test_vnpt.py`, `demo_audio/`, `DEMO.md`, `HANDOFF.md`, `TEST_GUIDE.md`, `TWILIO_SETUP.md`

---

## F. Giới hạn còn lại (trung thực)

- **Twilio trial**: chỉ gọi/nhắn số đã verify + có lời nhắn tiếng Anh đầu cuộc gọi → production cần nâng cấp tài khoản.
- **SMS tới số VN** bị gate (lỗi 21612) → dùng Telegram thay.
- **Telegram (demo) → Zalo (production)**: kiến trúc sẵn sàng; cần OA + template duyệt + thêm auto-refresh access_token (~30 dòng).
- **Deploy** (Railway/Render): đã có đủ file cấu hình + `DEPLOY.md`; chỉ cần `git push` lên GitHub rồi bấm deploy. SQLite trên free tier là filesystem tạm (reset khi redeploy) — production nên gắn disk/Postgres (đã ghi rõ trong `DEPLOY.md`).
- Cảnh báo người thân hiện gửi tới **1 chat_id chung**; production nên tách bảng `contacts` (one-to-many) lưu theo số điện thoại.

---

## G. Còn lại cho team

- **Dev 2**: tinh chỉnh synonym (`symptom_schema.py`); logic `chatbot_flow.py` đã có nền chạy được.
- **Dev 3**: cửa sổ chat nổi UI (💬 + nút 🎙️); các nút gọi điện/hẹn giờ/xóa đã wire sẵn backend.

---

## H. Kết luận

Toàn bộ nhiệm vụ Dev 1 trong file task **đã hoàn thành** (trừ deploy + history endpoint — optional / thay bằng ngrok). Làm thêm 8 tính năng vượt phạm vi, nổi bật: **tự động gọi điện thật theo lịch** và **cảnh báo người thân khi RED** — đều chạy thật, không mô phỏng.
