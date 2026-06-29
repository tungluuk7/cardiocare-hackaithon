# Ghi chú bàn giao — từ Dev 1 (Backend + VNPT Voice)

Cập nhật: 2026-06-29. Đọc cùng `DEMO.md` (cách chạy + kịch bản demo).

Phần backend + voice đã **chạy thật end-to-end với VNPT** (không còn mock bắt buộc).
File này tóm tắt: (1) cái gì đã đổi, (2) Dev 2 cần biết gì, (3) Dev 3 cần biết gì,
(4) việc còn lại.

---

## 0. TL;DR

- Backend chạy ổn: `POST /patients` (+ `DELETE`), `/calls/simulate`, `/dashboard`,
  `/alerts`, `/chatbot/*`, `POST /calls/{id}/callback` (voicebot gọi lại).
- **VNPT STT + TTS hoạt động thật** (`api.idg.vnpt.vn`). Lỗi 401 cũ đã sửa
  (thiếu header `Authorization: Bearer`).
- **TỰ ĐỘNG GỌI ĐIỆN THẬT theo giờ hẹn (Twilio)** — đã chạy thật, máy reo đúng giờ,
  ghi âm → VNPT STT → triage. Xem mục 4 + `TWILIO_SETUP.md`.
- **Matcher triệu chứng được nâng cấp** trong `services/smartbot_ner.py`
  (file của Dev 2) — xem mục Dev 2.
- Frontend `static/index.html` đã wire sẵn alerts + callback + nút gọi điện/hẹn
  giờ/xóa (xem mục Dev 3).
- Chạy demo: `.\run.ps1 -Seed` → http://localhost:8000/static/index.html

### File mới Dev 1 đã thêm
| File | Việc |
|---|---|
| `services/pipeline.py` | Pipeline dùng chung: (audio→STT) → triage → lưu DB → alert |
| `services/telephony.py` | Adapter Twilio: gọi ra, TwiML, tải ghi âm |
| `services/scheduler.py` | Vòng lặp nền tự gọi theo `call_time` (real/mô phỏng) |
| `api/telephony.py` | API gọi điện + lập lịch + webhook ghi âm Twilio |

---

## 1. File nào của ai

| File | Chủ | Trạng thái |
|---|---|---|
| `api/patients.py`, `api/calls.py`, `api/chatbot.py`, `api/telephony.py` | Dev 1 | ✅ xong |
| `services/vnpt_voice.py`, `alert.py`, `pipeline.py`, `telephony.py`, `scheduler.py` | Dev 1 | ✅ xong |
| `services/triage_engine.py`, `services/symptom_schema.py`, `services/chatbot_flow.py` | **Dev 2** | ✅ chạy được |
| `services/smartbot_ner.py` | **Dev 2** | ⚠️ Dev 1 đã sửa matcher — xem mục 2 |
| `static/index.html` | **Dev 3** | ✅ Dev 1 đã wire endpoint mới — xem mục 3 |
| `database.py`, `config.py`, `main.py` | Dev 1 (chung) | ✅ xong |

---

## 2. Gửi Dev 2 (Triage / NER)

### ⚠️ Mình đã sửa `services/smartbot_ner.py` — hàm `_extract_via_keywords`
Lý do: matcher cũ dùng **substring thuần** nên sót khi có từ chèn vào, ví dụ
"chân **cũng hơi** sưng" không khớp synonym "chân hơi sưng".

Cách mới (vẫn keyword-based, không gọi API):
- **Token-match có thứ tự**, cho chèn tối đa 1 từ đệm giữa 2 từ của 1 cụm synonym.
- **Lọc đại từ/sở hữu/kính ngữ** (`của, bác, tôi, dạ, thưa...`) trước khi khớp.
- **Phủ định** mở rộng: `không, chưa, hết, đỡ, giảm...` → bỏ qua triệu chứng.
- Đã test 9/9 ca (gồm ca bẫy an toàn: "đau lưng nhẹ ngực vẫn ổn" → GREEN, không
  bắt nhầm thành đau ngực).

**Contract KHÔNG đổi:** `extract_symptoms(transcript) -> list[str]` vẫn y nguyên.
Bạn không cần sửa `triage_engine.py`. Nếu muốn thêm triệu chứng/synonym, chỉ sửa
`symptom_schema.py` như cũ — matcher tự tận dụng.

### `triage_engine.analyze()` đang được gọi ở 2 nơi
- `api/calls.py` (luồng cuộc gọi) và `api/chatbot.py` (luồng chat). Cả hai đều
  dựa vào `TriageResult(level, symptoms, symptom_labels, message)`. Giữ nguyên
  shape này khi chỉnh sửa.

### Gợi ý nếu còn thời gian
- Thêm synonym vùng miền / cách nói của người già vào `symptom_schema.py`.
- Cân nhắc thêm mức độ tin cậy (confidence) — cột `triage_results.confidence` đã có
  sẵn trong DB nhưng hiện chưa dùng.

---

## 3. Gửi Dev 3 (Frontend)

`static/index.html` mình đã wire sẵn, **giữ nguyên style Tailwind của bạn**. Bạn có
thể tiếp tục đổi giao diện; chỉ cần giữ các lời gọi API dưới đây.

### Endpoint & contract

| Endpoint | Method | Dùng để |
|---|---|---|
| `/dashboard` | GET | Bảng bệnh nhân (RED→YELLOW→GREEN), có `call_time`, `last_answered_at` |
| `/patients` | GET/POST | List / tạo bệnh nhân |
| `/patients/{id}` | DELETE | Xóa bệnh nhân + dữ liệu liên quan (nút 🗑) |
| `/calls/simulate` | POST (form) | Upload audio hoặc `scenario` → triage |
| `/alerts` · `/alerts/{id}/seen` | GET / POST | Cảnh báo real-time / đánh dấu đã xem |
| `/calls/{id}/callback` | POST | Voicebot gọi lại → `{message, audio_url}` |
| `/callbacks/{id}.wav` | GET | File giọng nói gọi lại |
| `/telephony/status` | GET | real / simulation |
| `/telephony/schedule/{id}` | PUT | Hẹn giờ `{"call_time":"09:00"}` (nút 📅) |
| `/telephony/call/{id}` | POST | Gọi điện ngay (nút 📲) |
| `/telephony/run-now` | POST | Chạy vòng gọi các ca tới hạn (nút ▶) |

### Chatbot — cửa sổ chat nổi (Dev 3 làm UI, backend đã xong)
| Endpoint | Method | Dùng để |
|---|---|---|
| `/chatbot/opening` | GET | Câu chào đầu khi mở chat |
| `/chatbot/message` | POST | `{message, session_id, patient_id}` → `{reply, triage_level, symptoms, symptom_labels, turn}`. Tự cộng dồn triệu chứng qua các turn |
| `/chatbot/transcribe` | POST (multipart `audio`) | Nút 🎙️: audio → VNPT STT → `{text}` để điền vào ô chat |
| `/chatbot/alert-patient` | POST | `{patient_id, level, symptoms, symptom_labels}` → gửi cảnh báo (gắn đúng patient_id) |
| `/chatbot/session/{id}` | DELETE | Reset hội thoại khi đóng chat |

Khi `triage_level=RED`: đổi viền chat đỏ + gọi `/chatbot/alert-patient`. Logic hội
thoại (câu chào, follow-up, reply tự nhiên) nằm ở `services/chatbot_flow.py` — **Dev 2**.

### Field MỚI trong response `/calls/simulate`
```jsonc
{
  "level": "RED",
  "transcript": "...",
  "symptom_labels": ["Đau ngực", "Ngất / Mất ý thức"],
  "alert_sent": true,
  "callback_available": true   // ← MỚI: true khi RED/YELLOW → hiện nút "Gọi lại"
}
```

### Luồng callback (đã code sẵn trong `playCallback()`)
1. Bấm "📞 Gọi lại" → `POST /calls/{patient_id}/callback`
2. Nhận `{patient_name, level, message, audio_url}`
3. Mở modal, set `<audio src=audio_url>` và `audio.play()` (autoplay OK vì có click)
4. GREEN gọi callback sẽ trả **400** — frontend đã bắt lỗi, chỉ hiện nút cho RED/YELLOW.

### Field thời gian trong `/dashboard` (phân biệt rõ)
| Field | Ý nghĩa |
|---|---|
| `last_answered_at` | Thời điểm bệnh nhân **NHẤC MÁY** gần nhất (chỉ set khi trả lời cuộc gọi thật). Cột "Lần gọi cuối" ưu tiên hiện field này; chưa nhấc máy → "Chưa nhấc máy" |
| `last_call_at` | Thời điểm có triage gần nhất (call/chat) — fallback khi chưa có `last_answered_at` |
| `call_time` | Giờ hẹn gọi tự động "HH:MM" (null nếu chưa đặt) |

> `last_call_date` (chỉ trong DB, không trả ra dashboard) = ngày gọi đi để chống
> gọi trùng — KHÁC `last_answered_at` (lúc nhấc máy). Cuộc gọi nhỡ không cập nhật
> `last_answered_at`.

### Lưu ý nhỏ
- Alerts poll mỗi 5s, dashboard 10s (chỉnh trong `setInterval` cuối file).
- RED alert có class `.blink` (nhấp nháy) — CSS ở `<style>` đầu file.
- `audio_url` thêm `?t=Date.now()` để tránh cache khi gọi lại nhiều lần.
- Nút 📲/📅/▶/🗑 đã wire sẵn; badge góc phải hiện "📞 Gọi thật" / "🧪 Mô phỏng".

---

## 4. Tự động gọi điện thật (Twilio) — Dev 1

Đã chạy thật: scheduler tới giờ `call_time` → Twilio quay số → phát câu hỏi VNPT
TTS → ghi âm → VNPT STT → triage → cảnh báo. Chi tiết bật/cấu hình: `TWILIO_SETUP.md`.

- **Tự chọn chế độ:** đủ 3 biến `TWILIO_*` + `PUBLIC_BASE_URL` trong `.env` → gọi
  thật; thiếu → **mô phỏng** (scheduler vẫn chạy pipeline với mock để demo).
- **3 thứ phải cùng chạy khi gọi thật:** server + **ngrok** (giữ cửa sổ mở) +
  số đã verify trên Twilio trial.
- **Lập lịch:** `PUT /telephony/schedule/{id}` đặt `call_time`; vòng lặp nền
  (`services/scheduler.py`) kiểm tra mỗi 30s, gọi 1 lần/ngày/bệnh nhân.
- **VNPT vẫn là lõi:** Twilio chỉ là đường dây; câu hỏi = VNPT TTS, hiểu trả lời
  = VNPT STT.

---

## 4b. Cảnh báo phân mức + báo người thân

| Mức | Hành động |
|---|---|
| **RED** | Lưu DB (in-app alert) **+ nhắn tin cho người thân** |
| **YELLOW** | Chỉ lưu DB |
| **GREEN** | Không cảnh báo (không ghi DB) |

**Kênh báo người thân** — `services/alert.py::send_alert` → `_notify_family()`, ưu
tiên theo thứ tự (kênh nào cấu hình trước thì dùng):

1. **Zalo ZNS** (`services/zalo.py`) — cần OA + template duyệt + `family_phone`. *Chưa
   dùng được: không tạo được OA.*
2. **Telegram** (`services/telegram.py`) — ✅ **KÊNH ĐANG CHẠY THẬT**. Miễn phí,
   không bị gate ở VN. Cấu hình `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` trong `.env`.
3. **SMS Twilio** — `family_phone` + Twilio. *VN thường bị gate (lỗi 21612).*
4. **Mô phỏng** (log) nếu chưa cấu hình kênh nào.

- SĐT người thân: trường **`family_phone`** (`POST /patients` nhận thêm, optional) —
  dùng cho Zalo/SMS. Telegram gửi tới `TELEGRAM_CHAT_ID` (không cần `family_phone`).
- Lấy `chat_id`: bấm Start bot rồi chạy
  `python -c "from services import telegram; print(telegram.get_chat_ids())"`.

---

## 5. Việc còn lại / tuỳ chọn

| Việc | Ai | Ghi chú |
|---|---|---|
| Tinh chỉnh UI dashboard | Dev 3 | nền đã chạy, thoải mái design |
| Thêm synonym triệu chứng | Dev 2 | sửa `symptom_schema.py` |
| Public URL cho giám khảo + webhook Twilio | bất kỳ | `.\setup_ngrok.ps1` (DEMO.md / TWILIO_SETUP.md) |
| Gọi mọi số / bỏ lời nhắn trial | sau MVP | nâng cấp tài khoản Twilio (trial chỉ gọi số verify) |
| Email alert | — | đang bị mạng chặn; in-app alert là kênh chính |

---

## 6. Chạy & kiểm tra nhanh

```powershell
cd "C:\Users\Anh Quan\cardiocare"
.\run.ps1 -Seed                          # cài deps + seed + chạy server
# Kiểm tra VNPT:
.\.venv\Scripts\python test_vnpt.py      # kỳ vọng: TTS OK, STT OK, Triage RED
# Gọi điện thật: bật ngrok + cấu hình Twilio (TWILIO_SETUP.md)
```
Dashboard: http://localhost:8000/static/index.html · API docs: http://localhost:8000/docs

**Mọi thay đổi đều không phá contract cũ** — các phần Dev 2/Dev 3 đã làm vẫn chạy.
