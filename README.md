# CardioCare

Hệ thống trợ lý AI theo dõi bệnh nhân tim mạch cao tuổi trong 30 ngày sau xuất viện
(can thiệp mạch vành qua da — PCI/đặt stent). Hệ thống tự động gọi điện hỏi thăm bằng
giọng nói, trích xuất triệu chứng, phân loại mức độ ưu tiên và cảnh báo kịp thời cho
điều dưỡng và người thân khi phát hiện dấu hiệu nguy hiểm.

**Demo trực tuyến:** https://cardiocare-f2b2.onrender.com/static/index.html

---

## 1. Giới thiệu

Giai đoạn 30 ngày sau can thiệp mạch vành là "thời gian vàng" nhưng dễ bị đứt gãy theo
dõi: bệnh nhân cao tuổi ngại công nghệ, người thân không thể túc trực, điều dưỡng quá
tải. CardioCare lấp khoảng trống này bằng một quy trình khép kín:

1. **Số hóa hồ sơ** — OCR giấy ra viện để tạo nhanh hồ sơ bệnh nhân.
2. **Chủ động hỏi thăm** — voicebot gọi điện định kỳ, bệnh nhân chỉ cần nghe và trả lời.
3. **Phân loại thông minh** — nhận diện triệu chứng và xếp mức RED / YELLOW / GREEN.
4. **Cảnh báo kịp thời** — thông báo điều dưỡng và người thân ngay khi có ca nguy cấp.

---

## 2. Cài đặt và chạy

**Yêu cầu:** cài **Docker Desktop** (Cách A) *hoặc* **Python 3.12+** (Cách B) — không cần cả hai.

Lấy mã nguồn:

```bash
git clone https://github.com/tungluuk7/cardiocare-hackaithon.git
cd cardiocare-hackaithon
```

### Cách A — Docker (một lệnh, khuyến nghị)

```bash
docker compose up --build
```

### Cách B — Không dùng Docker (Python + venv, cũng một lệnh)

| Hệ điều hành | Lệnh |
|---|---|
| Linux / macOS | `bash run.sh --seed` |
| Windows (PowerShell) | `./run.ps1 -Seed` |

Script tự tạo virtualenv, cài phụ thuộc, nạp dữ liệu demo rồi khởi động server.

Sau khi chạy (cách nào cũng vậy), mở **http://localhost:8000/static/index.html**.

Ứng dụng hoạt động ngay cả khi chưa có tệp `.env` (chế độ dự phòng: giọng nói gTTS,
phân loại theo từ khóa, gọi điện mô phỏng). Để bật đầy đủ các dịch vụ VNPT, Twilio,
Telegram, tạo `.env` từ `.env.example` và điền khóa — xem `docs/SMARTUX_SETUP.md`,
`docs/TWILIO_SETUP.md`.

Các giao diện chính:

| Giao diện | Đường dẫn |
|---|---|
| Bảng điều khiển điều dưỡng | `/static/index.html` |
| Cửa sổ chat bệnh nhân | `/static/phone.html` |
| Báo cáo trải nghiệm (UX) | `/static/ux.html` |
| Tài liệu API | `/docs` |

---

## 3. Kiểm thử tự động

| Môi trường | Lệnh |
|---|---|
| Windows | `./run_tests.ps1` |
| Linux / macOS | `bash run_tests.sh` |
| Đã cài phụ thuộc | `pytest` |
| Docker | `docker compose run --rm cardiocare pytest` |

> Trên Windows, nếu PowerShell chặn chạy script (execution policy):
> `powershell -ExecutionPolicy Bypass -File run_tests.ps1` (tương tự cho `run.ps1`).

Bộ kiểm thử trong `tests/` chạy hoàn toàn ngoại tuyến và tất định (không cần khóa API):
phân loại RED/YELLOW/GREEN kèm xử lý phủ định và tiếng Việt không dấu, bóc tách OCR
giấy ra viện trên nhiều bố cục, ràng buộc dữ liệu bệnh nhân, phân tích UX, và luồng
hội thoại của chatbot.

---

## 4. Cấu trúc dự án

```
.
├── api/              # Định tuyến FastAPI: patients, calls, chatbot, telephony, ux, ocr
├── services/         # Nghiệp vụ: triage, VNPT SmartVoice/SmartReader, alert, scheduler...
├── static/           # Giao diện web: dashboard, trang bệnh nhân, chat, báo cáo UX
├── tests/            # Kiểm thử tự động (pytest)
├── scripts/          # Công cụ hỗ trợ, script chạy tay (ngrok, smoke test)
├── docs/             # Tài liệu triển khai, demo, cấu hình, cơ sở tri thức
├── main.py           # Điểm khởi động ứng dụng
├── config.py         # Cấu hình & biến môi trường
├── database.py       # Khởi tạo cơ sở dữ liệu (SQLite)
├── seed_demo.py      # Nạp dữ liệu bệnh nhân mẫu
├── Dockerfile · docker-compose.yml
└── run.ps1 · run.sh · run_tests.ps1 · run_tests.sh
```

---

## 5. Tính năng chính

- **Voicebot tự động gọi** theo lịch (VNPT SmartVoice TTS/STT + Twilio): hỏi thăm, ghi
  âm câu trả lời và chuyển thành văn bản.
- **Bộ phân loại triệu chứng** theo quy tắc y khoa (VNPT Smartbot NER, dự phòng từ khóa),
  xử lý phủ định và tiếng Việt không dấu.
- **Cảnh báo đa kênh** khi RED: Telegram / Zalo / SMS cho người thân, đồng thời voicebot
  gọi lại bệnh nhân.
- **Chatbot hỏi thăm** (văn bản và giọng nói qua Web Speech tiếng Việt), cộng dồn triệu
  chứng qua nhiều lượt trao đổi.
- **OCR giấy ra viện** (VNPT SmartReader) tạo nhanh hồ sơ bệnh nhân, điều dưỡng rà soát
  trước khi lưu.
- **Đo lường trải nghiệm** bằng VNPT SmartUX kết hợp lớp thu thập nội bộ (thời gian phản
  ứng với ca nguy cấp, mức độ tương tác).

---

## 6. Hướng dẫn thao tác từng chức năng

Sau khi chạy (mục 2), mở **http://localhost:8000/static/index.html**. Dữ liệu demo đã
được nạp sẵn, có thể thao tác ngay. Với các chức năng gọi qua API, mở **/docs** (Swagger)
— bấm *Try it out* trên từng endpoint là chạy được, không cần công cụ ngoài.

### 6.1. Xem & phân luồng bệnh nhân (Bảng điều khiển điều dưỡng)

1. Mở `/static/index.html`.
2. Ba thẻ trên cùng **Cờ Đỏ / Vàng / Xanh** hiển thị số ca theo mức ưu tiên. Bấm một
   thẻ để **lọc** danh sách theo mức đó; bấm **Hiện tất cả** để bỏ lọc.
3. Bấm **Làm mới** để nạp lại hàng đợi mới nhất.
4. Mỗi dòng bệnh nhân hiển thị triệu chứng AI trích xuất và thời điểm tương tác cuối.
   Bấm **tên bệnh nhân** để xem timeline chi tiết (mục 6.5).

### 6.2. Gọi lại bệnh nhân ngay (voicebot)

1. Trên mỗi dòng bệnh nhân, bấm **Gọi lại ngay**.
2. Nếu **chưa** cấu hình Twilio: hệ thống chạy **mô phỏng** — sinh một cuộc gọi giả,
   phân loại triệu chứng và cập nhật ngay lên dashboard (bấm *Làm mới* để thấy).
3. Nếu **đã** cấu hình Twilio (xem `docs/TWILIO_SETUP.md`): voicebot gọi thật tới số
   bệnh nhân.
4. Tương đương qua API: `POST /telephony/call/{patient_id}`.

### 6.3. Đặt lịch tự động gọi định kỳ

1. Mở `/docs` → nhóm **telephony**.
2. `PUT /telephony/schedule/{patient_id}` với `call_time` dạng **HH:MM** (giờ Hà Nội,
   UTC+7) để đặt giờ gọi hằng ngày.
3. Bộ lập lịch chạy nền, cứ ~30 giây quét một lần và gọi những bệnh nhân đến giờ mà
   hôm nay chưa gọi.
4. Để **demo ngay không cần chờ tới giờ**: gọi `POST /telephony/run-now` để chạy ngay
   một vòng cho các ca đến hạn. Xem trạng thái bộ lập lịch qua `GET /telephony/status`.

### 6.4. Chatbot hỏi thăm (mô phỏng cuộc gọi trên điện thoại)

1. Mở `/static/phone.html` (hoặc bấm **Mô phỏng điện thoại** ở thanh bên).
2. Chọn bệnh nhân ở ô trên cùng — trợ lý sẽ mở lời chào hỏi thăm.
3. **Nhập bằng chữ**: gõ câu trả lời như bệnh nhân (ví dụ *"tôi bị đau ngực và khó thở"*)
   rồi gửi. Thanh phân loại dưới khung chat đổi màu **VÀNG/ĐỎ** theo mức nguy cấp và liệt
   kê triệu chứng nhận diện được; triệu chứng cộng dồn qua nhiều lượt.
4. **Nhập bằng giọng nói**: bấm nút **micro**, nói, rồi bấm dừng — hệ thống chuyển giọng
   nói thành văn bản và xử lý như trên.
5. Khi lên mức **ĐỎ**, ca này cũng xuất hiện ở nhóm Cờ Đỏ trên dashboard.

### 6.5. Xem lịch sử & timeline một bệnh nhân

- Từ dashboard bấm tên bệnh nhân, hoặc mở `/static/patient.html?id=<id>`.
- Trang hiển thị toàn bộ cuộc gọi, bản ghi hội thoại và kết quả triage theo thời gian.
- Qua API: `GET /patients/{id}/history`.

### 6.6. Thêm bệnh nhân mới

- Mở `/docs` → `POST /patients`, điền tối thiểu `name` và `phone` (kèm `age`,
  `diagnosis`, `family_phone`… nếu có). `family_phone` là số người thân nhận cảnh báo khi RED.

### 6.7. Số hóa giấy ra viện bằng OCR

1. Mở `/docs` → nhóm **ocr**. `GET /ocr/status` cho biết OCR đang chạy chế độ thật (có
   khóa VNPT SmartReader) hay mô phỏng.
2. Dùng endpoint OCR để tải ảnh **giấy ra viện** lên — hệ thống trả về **bản nháp** hồ sơ
   (chẩn đoán, ngày ra viện…).
3. Đây là quy trình *human-in-the-loop*: điều dưỡng **rà soát và chỉnh** bản nháp trước
   khi lưu; OCR **không** tự ghi đè hồ sơ.

### 6.8. Cảnh báo khi có ca nguy cấp (RED)

- Khi một lượt hỏi thăm cho kết quả **ĐỎ**, hệ thống tự tạo cảnh báo trong ứng dụng (hiện
  trên dashboard) — luôn chạy, không cần cấu hình gì.
- Nếu đã cấu hình kênh ngoài, cảnh báo còn gửi tới người thân qua **Telegram / Zalo / SMS**
  và voicebot gọi lại bệnh nhân. Thiếu khóa thì các kênh này chạy mô phỏng (ghi log).

### 6.9. Báo cáo trải nghiệm (UX)

- Mở `/static/ux.html` để xem các chỉ số trải nghiệm: thời gian phản ứng với ca nguy cấp,
  mức độ tương tác… (kết hợp VNPT SmartUX khi có cấu hình).

---

## 7. Giới hạn hiện tại (MVP)

Đây là bản MVP xây trong khuôn khổ hackathon. Một số mặt còn giới hạn, cũng là hướng
phát triển tiếp theo:

- **Hội thoại chưa thật tự nhiên.** Smartbot/voicebot bám kịch bản hỏi–đáp theo luồng
  cố định, chưa xử lý mượt khi bệnh nhân cao tuổi trả lời lan man, ngắt lời hay hỏi
  ngược. Nhận diện triệu chứng thiên về quy tắc/từ khóa nên có thể bỏ sót cách diễn đạt
  dân dã, vùng miền.
- **Dashboard gộp chung, chưa phân vai.** Giao diện điều dưỡng và trang bệnh nhân/chat
  dùng chung một ứng dụng, chưa có đăng nhập, phân quyền hay tách biệt dữ liệu theo vai
  trò (bác sĩ / điều dưỡng / bệnh nhân / người thân).
- **OCR mới đọc giấy ra viện.** Bộ số hóa hiện chỉ bóc tách *giấy báo ra viện* theo một
  số bố cục quen thuộc; chưa đọc đơn thuốc, kết quả xét nghiệm hay chữ viết tay, và vẫn
  cần điều dưỡng rà soát trước khi lưu.
- **Phụ thuộc cấu hình dịch vụ ngoài.** Gọi điện thật, giọng nói/OCR/NLP chất lượng cao
  và cảnh báo người thân chỉ bật khi có khóa API; thiếu khóa thì các phần này chạy mô
  phỏng để phục vụ demo.
- **Lưu trữ đơn giản.** Dùng SQLite một tệp — đủ cho demo nhưng chưa tối ưu cho nhiều
  người dùng đồng thời hoặc triển khai quy mô bệnh viện.

---

## 8. Kiến trúc và công nghệ

Kiến trúc hướng sự kiện gồm bốn phân hệ: thu thập dữ liệu → trích xuất bằng AI → động cơ
phân loại → điểm chạm đa kênh.

**Công nghệ:** Python · FastAPI · SQLite · VNPT SmartVoice / SmartReader / SmartUX /
Smartbot · Twilio · Telegram.

---

## 9. Tài liệu

| Tài liệu | Nội dung |
|---|---|
| `docs/DEMO.md` | Hướng dẫn demo và kịch bản trình diễn |
| `docs/DEPLOY.md` | Hướng dẫn triển khai (Render / Railway) |
| `docs/TWILIO_SETUP.md` | Cấu hình gọi điện thật qua Twilio |
| `docs/SMARTUX_SETUP.md` | Cấu hình đo trải nghiệm VNPT SmartUX |
| `docs/cardiocare_tri_thuc.md` | Cơ sở tri thức phân loại triệu chứng |
