# CardioCare — Hướng dẫn Demo Hackathon

Hệ thống AI theo dõi bệnh nhân tim mạch sau xuất viện (sau PCI). Voicebot **tự động
gọi điện thật** (theo giờ hẹn) → đọc câu hỏi bằng VNPT TTS → nhận diện câu trả lời
bằng VNPT STT → phân tích triệu chứng → phân loại **RED / YELLOW / GREEN** → cảnh
báo điều dưỡng real-time trên dashboard, và voicebot gọi lại trấn an khi nguy hiểm.

> Quay số thật dùng **Twilio** (đường dây điện thoại); **VNPT** là lõi nghe-hiểu
> tiếng Việt. Xem `TWILIO_SETUP.md` để bật gọi thật. Không có Twilio → vẫn demo
> được bằng upload audio / kịch bản (chế độ mô phỏng).

---

## 0. Chuẩn bị (làm 1 lần trước hôm thi)

```powershell
cd "C:\Users\Anh Quan\cardiocare"
.\run.ps1 -Seed          # cài deps + tạo dữ liệu demo + khởi động server
```

Mở trình duyệt: **http://localhost:8000/static/index.html**

> Lần đầu chạy sẽ cài thư viện (~1 phút). Các lần sau chạy `.\run.ps1` là xong.

### Kiểm tra VNPT hoạt động (nên chạy thử trước khi thi)

```powershell
$env:PYTHONUTF8=1
.\.venv\Scripts\python test_vnpt.py
```

Kỳ vọng: `TTS OK`, `STT OK`, `Triage RED`. Nếu lỗi mạng/token, hệ thống tự
chuyển sang chế độ mock (xem mục 4) — demo vẫn chạy được.

### Nếu muốn demo GỌI ĐIỆN THẬT (Twilio) — cần thêm
1. Cấu hình Twilio trong `.env` (xem `TWILIO_SETUP.md`)
2. **ngrok phải đang chạy** suốt buổi demo, giữ cửa sổ mở:
   ```powershell
   .\ngrok.exe http --url=<domain-cua-ban>.ngrok-free.dev 8000
   ```
3. Kiểm tra: mở `https://<domain>/health` ra `{"status":"ok"}` và
   `GET /telephony/status` trả `"mode":"real"`.
4. Số gọi tới phải là số **đã verify** trên Twilio trial.

> 3 thứ phải CÙNG chạy khi gọi thật: **server** + **ngrok** + **số đã verify**.
> Thiếu ngrok → cuộc gọi reo nhưng không phát được câu hỏi / không nhận ghi âm.

---

## 1. Luồng demo chính (5 phút)

### Cảnh 1 — Dashboard tổng quan (30s)
Mở dashboard. Có sẵn 5 bệnh nhân, sắp xếp theo mức độ ưu tiên:
- 🔴 **Lê Văn Cường** — RED (đau ngực, ngất, khó thở) — nổi bật trên cùng
- 🟡 Trần Thị Bình, Phạm Thị Dung — YELLOW (cần theo dõi)
- 🟢 Nguyễn Văn An, Hoàng Văn Em — GREEN (ổn định)

**Câu nói:** "Điều dưỡng nhìn 1 màn hình là biết ai cần xử lý trước. Đỏ lên đầu."

### Cảnh 2 — Mô phỏng cuộc gọi tự động (90s)
Đây là phần lõi. Có 2 cách trình diễn:

**Cách A — Upload audio thật (ấn tượng nhất):**
1. Bấm nút **"Mô phỏng cuộc gọi"** trên 1 bệnh nhân
2. Upload file audio bệnh nhân trả lời (có sẵn `demo_audio/patient_red.wav`)
3. Hệ thống chạy: **VNPT STT** → transcript hiện lên → **triage** → badge đổi màu
4. Nếu RED/YELLOW → **cảnh báo nhấp nháy** xuất hiện ngay

**Cách B — Kịch bản nhanh (không cần file):**
1. Bấm "Mô phỏng cuộc gọi" → chọn kịch bản **RED**
2. Transcript mẫu hiện lên → triage RED → alert gửi

**Câu nói:** "Cuộc gọi thật dùng VNPT SmartVoice — chuyển văn bản câu hỏi thành
giọng nói gọi cho cụ, rồi nhận diện câu trả lời. Mình demo bằng audio thu sẵn."

### Cảnh 3 — Cảnh báo & gọi lại tự động (90s)
1. Chuông cảnh báo RED nhấp nháy ở góc dashboard
2. Bấm vào cảnh báo → xem chi tiết: tên, SĐT, triệu chứng, lời khuyên
3. Bấm **"Gọi lại bệnh nhân"** → hệ thống **sinh lời nhắn thoại cá nhân hoá**
   bằng VNPT TTS và **phát ngay** (mô phỏng voicebot gọi lại cụ):
   > *"Xin chào bác Lê Văn Cường. Chúng tôi ghi nhận bác đang có dấu hiệu đau ngực,
   > ngất, khó thở. Đây là tình trạng cần xử lý ngay. Điều dưỡng sẽ gọi lại cho bác
   > trong ít phút. Nếu nặng hơn, xin gọi ngay 115..."*
4. Bấm "Đã xem" → cảnh báo chuyển trạng thái

**Câu nói:** "0% bỏ sót ca nguy hiểm. Phát hiện RED là voicebot tự gọi lại cụ ngay
bằng giọng nói thật của VNPT — trấn an, hướng dẫn gọi 115 — đồng thời báo điều dưỡng.
Lời nhắn được cá nhân hoá theo đúng triệu chứng của từng người."

### Cảnh 4 — ⭐ Tự động gọi điện THẬT theo giờ (điểm nhấn)
Cần Twilio đã cấu hình + server + **ngrok đang chạy** (xem `TWILIO_SETUP.md`).
1. Trên dashboard, bấm **📅 Hẹn giờ** cho 1 bệnh nhân (số đã verify) → đặt giờ =
   **giờ hiện tại + 2 phút**
2. Để yên — tới đúng giờ, hệ thống **tự gọi** (không bấm gì): điện thoại reo
3. Nhấc máy → (bấm `1` qua lời nhắn trial) → nghe **câu hỏi tiếng Việt (VNPT TTS)**
4. Trả lời rõ ràng sau bíp: *"Tôi bị đau ngực và khó thở"* → cúp máy
5. Vài giây sau dashboard **tự cập nhật** triage + cảnh báo

> Muốn gọi ngay không chờ: bấm **📲 Gọi điện** trên dòng bệnh nhân, hoặc
> **▶ Chạy vòng gọi ngay** trên header.

**Câu nói:** "Hệ thống tự gọi điện cho cụ đúng giờ hẹn mỗi ngày — không cần điều
dưỡng quay số. Cụ trả lời bằng giọng nói, AI VNPT nghe hiểu và phân loại nguy cơ
ngay. Đây là tự động hoá thật, gọi vào số điện thoại thật."

### Cảnh 5 — Chatbot (tuỳ chọn, 60s)
Mở cửa sổ chat nổi → gõ "bác bị đau ngực" → bot phản hồi + tự động flag RED.

**Câu nói:** "Người nhà cũng có thể nhắn tin trực tiếp, cùng một bộ não phân tích."

> **Nói rõ khi trả lời điện thoại:** chờ tiếng bíp, nói chậm, dùng đúng từ khoá
> (đau ngực, khó thở, chóng mặt, sưng chân). Nói không rõ → STT bắt sai.

---

## 2. Public URL — cho giám khảo thử trên điện thoại

### Cách 1 — ngrok (bạn đã yêu cầu)
```powershell
.\setup_ngrok.ps1                                   # tải ngrok (1 lần)
.\ngrok.exe config add-authtoken <TOKEN_CUA_BAN>    # authtoken miễn phí
.\run.ps1 -Share                                    # chạy server + tunnel
```
Public URL sẽ hiện ra (dạng `https://xxxx.ngrok-free.app`). Dashboard tại
`<url>/static/index.html`. Lấy authtoken: https://dashboard.ngrok.com/get-started/your-authtoken

### Cách 2 — Cloudflare Tunnel (KHÔNG cần tài khoản)
```powershell
winget install --id Cloudflare.cloudflared
# chạy server ở 1 cửa sổ:
.\run.ps1
# cửa sổ khác:
cloudflared tunnel --url http://localhost:8000
```
Nó in ra URL `https://xxx.trycloudflare.com` dùng ngay, không đăng ký.

> **Lưu ý:** Dashboard chạy được offline (localhost). NHƯNG nếu demo **gọi điện
> thật (Twilio)** thì **bắt buộc có ngrok** — Twilio cần URL công khai để lấy câu
> hỏi và gửi file ghi âm về. Giữ cửa sổ ngrok mở suốt buổi demo.

---

## 3. Lệnh nhanh (cheat sheet)

| Việc cần làm | Lệnh |
|---|---|
| Khởi động server | `.\run.ps1` |
| Reset + seed dữ liệu demo | `.\run.ps1 -Seed` |
| Server + public URL | `.\run.ps1 -Share` |
| Chỉ seed lại dữ liệu | `.\.venv\Scripts\python seed_demo.py --reset` |
| Test VNPT TTS/STT | `.\.venv\Scripts\python test_vnpt.py` |
| Dashboard | http://localhost:8000/static/index.html |
| API docs (Swagger) | http://localhost:8000/docs |

### Endpoint cho Dev 3 (frontend)
| Endpoint | Công dụng |
|---|---|
| `GET /dashboard` | Danh sách bệnh nhân, sắp xếp RED→YELLOW→GREEN (có `call_time`) |
| `POST /calls/simulate` | Upload audio / scenario → triage (trả thêm `callback_available`) |
| `GET /alerts` · `POST /alerts/{id}/seen` | Cảnh báo real-time / đánh dấu đã xem |
| `POST /calls/{id}/callback` | **Voicebot gọi lại** → `{message, audio_url}`, phát qua `<audio>` |
| `DELETE /patients/{id}` | Xóa bệnh nhân + dữ liệu liên quan (nút 🗑) |
| `GET /telephony/status` | real / simulation |
| `PUT /telephony/schedule/{id}` | Hẹn giờ gọi `{"call_time":"09:00"}` (nút 📅) |
| `POST /telephony/call/{id}` | Gọi điện ngay 1 bệnh nhân (nút 📲) |
| `POST /telephony/run-now` | Chạy vòng gọi các ca tới hạn (nút ▶) |

> Webhook nội bộ (không phải Dev 3 gọi): `GET /telephony/question.wav` (Twilio phát
> câu hỏi), `POST /telephony/twilio-recording` (Twilio gửi ghi âm về).

---

## 4. Chế độ an toàn khi mạng/VNPT trục trặc

Nếu hội trường mạng yếu hoặc token VNPT hết hạn, bật chế độ mock — bỏ qua audio,
dùng kịch bản dựng sẵn (transcript vẫn thật, triage vẫn thật):

Sửa file `.env`, thêm dòng:
```
USE_MOCK_AUDIO=true
```
Rồi demo bằng **Cách B** (chọn kịch bản RED/YELLOW/GREEN). Không ai biết là mock
vì toàn bộ phân tích & cảnh báo vẫn chạy thật.

---

## 5. Kiến trúc (nếu giám khảo hỏi kỹ thuật)

```
Scheduler (tới giờ hẹn call_time)  ── tự động, kiểm tra mỗi 30s
   ▼
Twilio  ── quay số THẬT → điện thoại bệnh nhân reo        [đường dây]
   │  <Play> câu hỏi (VNPT TTS)  →  <Record> ghi âm trả lời
   ▼
Webhook /telephony/twilio-recording  ── tải file ghi âm
   ▼
VNPT SmartVoice STT  ── giọng nói → văn bản tiếng Việt    [api.idg.vnpt.vn, lõi]
   ▼
NER + keyword matching (8 nhóm triệu chứng, có lọc từ đệm + phủ định)
   ▼
Triage Engine  ── RED / YELLOW / GREEN (rule-based, minh bạch)
   │
   ├─► Lưu DB (SQLite)
   ├─► Alert real-time ──► Dashboard điều dưỡng
   └─► Voicebot gọi lại (VNPT TTS) khi RED/YELLOW
```

**Stack:** Python + FastAPI + SQLite + VNPT SmartVoice (TTS/STT) + Twilio (telephony).
**Vì sao rule-based triage:** y tế cần minh bạch, giải thích được, 0% bỏ sót ca
RED. Không dùng black-box. Có bác sĩ trong vòng lặp (human-in-the-loop) ở pilot.
