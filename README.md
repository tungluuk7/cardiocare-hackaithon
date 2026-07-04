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

## 2. Cài đặt và chạy (một lệnh)

### Docker

```bash
docker compose up --build
```
Sau khi chạy, mở **http://localhost:8000/static/index.html**.

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

## 6. Kiến trúc và công nghệ

Kiến trúc hướng sự kiện gồm bốn phân hệ: thu thập dữ liệu → trích xuất bằng AI → động cơ
phân loại → điểm chạm đa kênh.

**Công nghệ:** Python · FastAPI · SQLite · VNPT SmartVoice / SmartReader / SmartUX /
Smartbot · Twilio · Telegram.

---

## 7. Tài liệu

| Tài liệu | Nội dung |
|---|---|
| `docs/DEMO.md` | Hướng dẫn demo và kịch bản trình diễn |
| `docs/DEPLOY.md` | Hướng dẫn triển khai (Render / Railway) |
| `docs/TWILIO_SETUP.md` | Cấu hình gọi điện thật qua Twilio |
| `docs/SMARTUX_SETUP.md` | Cấu hình đo trải nghiệm VNPT SmartUX |
| `docs/cardiocare_tri_thuc.md` | Cơ sở tri thức phân loại triệu chứng |
