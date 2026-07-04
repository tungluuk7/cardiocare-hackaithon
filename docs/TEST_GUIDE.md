# Hướng dẫn tự test mục tiêu 3 ngày (Dev 1)

Cách dễ nhất: dùng **Swagger UI** — trang web tự sinh cho mọi API, bấm chuột là test.
Không cần gõ lệnh.

## Chuẩn bị (1 phút)

1. Đảm bảo server đang chạy. Nếu chưa, mở PowerShell:
   ```powershell
   cd "C:\Users\Anh Quan\cardiocare"
   .\run.ps1 -Seed
   ```
   (Nếu server đã chạy rồi thì bỏ qua.)

2. Mở 2 tab trình duyệt:
   - **Swagger** (để test API): http://localhost:8000/docs
   - **Dashboard** (để xem kết quả): http://localhost:8000/static/index.html

> Cách bấm trên Swagger: click vào 1 endpoint để mở → nút **"Try it out"** →
> điền dữ liệu → nút **"Execute"** → xem mục **"Response body"** và **"Code 200/201"**.

---

# 📅 NGÀY 1

## Test 1.1 — POST /patients tạo được bệnh nhân
1. Swagger → mở **POST /patients** → **Try it out**
2. Dán vào ô Request body:
   ```json
   { "name": "Bệnh nhân Test", "phone": "0900000999", "age": 70 }
   ```
3. **Execute**
4. ✅ **ĐẠT nếu:** Code = **201**, Response body có `"id"` (vd `"id": 6`).
   Ghi nhớ số id này.

## Test 1.2 — GET /patients trả về list
1. Swagger → mở **GET /patients** → **Try it out** → **Execute**
2. ✅ **ĐẠT nếu:** Code = **200**, Response body là một danh sách `[...]`, và có
   "Bệnh nhân Test" bạn vừa tạo ở trong đó.

## Test 1.3 — Mock STT trả đúng transcript
Mock STT chạy khi `POST /calls/simulate` **không** kèm file audio mà chỉ có `scenario`.
1. Swagger → mở **POST /calls/simulate** → **Try it out**
2. Điền form:
   - `patient_id` = id bạn tạo ở Test 1.1
   - `scenario` = `green`
   - (bỏ trống `audio_file`)
3. **Execute**
4. ✅ **ĐẠT nếu:** Response `"transcript"` = *"Bác cảm thấy bình thường, ăn uống được, đi lại nhẹ nhàng."*
5. Làm lại với `scenario` = `yellow` và `red`, transcript phải khác nhau đúng kịch bản:
   - yellow → "...hơi khó thở...chân cũng hơi sưng."
   - red → "...đau ngực dữ dội...ngất một lần...khó thở."

---

# 📅 NGÀY 2

## Test 2.1 — simulate "red" → lưu DB → dashboard hiện màu đỏ
1. Swagger → **POST /calls/simulate** → **Try it out**
   - `patient_id` = id "Bệnh nhân Test"
   - `scenario` = `red`
   - **Execute**
2. ✅ **Bước A (triage):** Response có `"level": "RED"` và `"symptom_labels"` gồm
   Đau ngực / Ngất / Khó thở.
3. ✅ **Bước B (lưu DB):** Response có `"call_log_id"` (1 số). Để chắc chắn đã ghi DB:
   mở **GET /calls/{call_log_id}** → nhập số đó → Execute → thấy `level = RED` và
   `transcript`. Nghĩa là đã lưu vào bảng `call_logs` + `triage_results`.
4. ✅ **Bước C (dashboard):** Mở tab **Dashboard**, nhấn F5. "Bệnh nhân Test" phải:
   - Nhảy **lên đầu bảng**
   - Có badge đỏ **🔴 KHẨN CẤP**
   - Ô "Khẩn cấp" ở thống kê tăng thêm 1

---

# 📅 NGÀY 3 (tích hợp VNPT thật + cảnh báo + gọi lại)

## Test 3.1 — VNPT STT + TTS thật chạy được
Chạy script kiểm tra trong PowerShell:
```powershell
cd "C:\Users\Anh Quan\cardiocare"
.\.venv\Scripts\python scripts\test_vnpt.py
```
✅ **ĐẠT nếu** in ra:
```
[1] TTS OK — sinh ... bytes audio
[2] STT OK — nhan dien: "Bác đau ngực dữ dội..."
[3] Triage: RED — [...]
KET QUA: TAT CA OK
```

## Test 3.2 — Upload audio THẬT → VNPT STT → triage
1. Swagger → **POST /calls/simulate** → **Try it out**
   - `patient_id` = id bất kỳ
   - `audio_file` → **Choose File** → chọn `demo_audio\patient_red.wav`
   - (bỏ trống `scenario`)
   - **Execute**
2. ✅ **ĐẠT nếu:** `"transcript"` ra đúng nội dung file (về đau ngực/ngất/khó thở),
   `"level": "RED"`. Đây là VNPT nhận diện giọng nói thật, không phải mock.

## Test 3.3 — Cảnh báo real-time trên dashboard
1. Mở tab **Dashboard**.
2. ✅ **ĐẠT nếu:** Ngay đầu trang có banner cảnh báo:
   - 🚨 đỏ **nhấp nháy** cho ca RED
   - ⚠️ vàng cho ca YELLOW
   - Mỗi banner có nút "📞 Gọi lại" và "Đã xem".
3. Bấm **"Đã xem"** trên 1 cảnh báo → nó biến mất (đã gọi `POST /alerts/{id}/seen`).

## Test 3.4 — Voicebot gọi lại bệnh nhân (TTS cá nhân hóa)
1. Trên Dashboard, ở dòng bệnh nhân RED (Lê Văn Cường), bấm **"📞 Gọi lại"**.
2. ✅ **ĐẠT nếu:** Hiện cửa sổ "Voicebot đang gọi lại", có:
   - Lời nhắn chữ (đọc được tên bệnh nhân + triệu chứng + nhắc gọi 115)
   - Trình phát audio **tự phát giọng nói** lời nhắn đó.
3. Thử bấm "📞 Gọi lại" ở 1 bệnh nhân GREEN (nếu có nút) → phải báo lỗi/không gọi
   (vì GREEN không cần gọi lại — backend trả 400).

## Test 3.5 — Chatbot (tùy chọn)
1. Swagger → **POST /chatbot/message** → **Try it out**
   ```json
   { "message": "bác bị đau ngực", "session_id": "test1", "patient_id": 3 }
   ```
2. ✅ **ĐẠT nếu:** Response có `"triage_level": "RED"` và `"reply"` là câu trả lời
   tự nhiên cảnh báo nguy hiểm.

---

## Bảng tick nhanh

| Ngày | Mục tiêu | Đạt? |
|---|---|---|
| 1 | POST /patients tạo bệnh nhân (201 + id) | ☐ |
| 1 | GET /patients trả list | ☐ |
| 1 | Mock STT đúng transcript (green/yellow/red) | ☐ |
| 2 | simulate red → level RED | ☐ |
| 2 | Lưu DB (GET /calls/{id} thấy dữ liệu) | ☐ |
| 2 | Dashboard hiện bệnh nhân đỏ | ☐ |
| 3 | VNPT TTS+STT thật (test_vnpt.py) | ☐ |
| 3 | Upload audio thật → triage | ☐ |
| 3 | Cảnh báo real-time + đã xem | ☐ |
| 3 | Voicebot gọi lại phát audio | ☐ |

## Khi xong nhớ reset dữ liệu sạch cho demo
```powershell
.\.venv\Scripts\python seed_demo.py --reset
```
(Vì test ở trên có tạo thêm "Bệnh nhân Test" và vài call log.)
