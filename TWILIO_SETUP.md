# Gọi điện thật bằng Twilio Trial (cấp số ngay)

Hệ thống tự ưu tiên Twilio khi có đủ 3 biến `TWILIO_*` trong `.env`. Làm theo:

## Bước 1 — Tạo tài khoản trial
1. Đăng ký: https://www.twilio.com/try-twilio (miễn phí, được ~15$ credit)
2. Xác minh email + **số điện thoại của bạn** (số `0975261207`). Số bạn dùng để
   đăng ký sẽ tự thành **Verified Caller ID** — đây chính là số sẽ nhận cuộc gọi.

## Bước 2 — Lấy thông tin từ Console
Vào https://console.twilio.com, ở trang chính (Account Info) copy:
- **Account SID** (bắt đầu `AC...`)
- **Auth Token** (bấm hiện)

## Bước 3 — Lấy số Twilio (số gọi đi / From)
1. Console → **Phone Numbers → Manage → Buy a number** (trial dùng credit, $0).
2. Chọn 1 số có khả năng **Voice** (số Mỹ `+1...` là được).
3. Copy số đó (dạng `+1...`).

## Bước 4 — ⚠️ BẬT quyền gọi đi Việt Nam (rất quan trọng)
Trial mặc định CHẶN gọi quốc tế. Phải bật thủ công:
- Console → **Voice → Settings → Geographic Permissions** (Geo Permissions)
- Tích **Vietnam** → Save.
- Nếu không bật, gọi vào `+84...` sẽ bị từ chối.

## Bước 5 — Verify số bạn sẽ nhận cuộc gọi
Trial chỉ gọi được số đã verify:
- Console → **Phone Numbers → Manage → Verified Caller IDs** → **Add a number**
- Nhập `+84975261207` → Twilio gọi/nhắn mã → nhập mã xác nhận.
- (Số đăng ký tài khoản thường đã được verify sẵn — kiểm tra ở đây.)

## Bước 6 — Điền `.env`
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
PUBLIC_BASE_URL=https://attain-anthill-clubbing.ngrok-free.dev
```
Lưu, rồi **khởi động lại server**:
```powershell
.\run.ps1 -Seed
```

## Bước 7 — Đảm bảo ngrok đang trỏ vào server
Cửa sổ khác chạy ngrok (port 8000):
```powershell
.\ngrok.exe http 8000
```
Mở `https://attain-anthill-clubbing.ngrok-free.dev/health` → phải thấy `{"status":"ok"}`.
(Nếu URL ngrok đổi, cập nhật lại `PUBLIC_BASE_URL` rồi restart server.)

## Bước 8 — Gọi thử
1. Dashboard → badge góc phải phải hiện **📞 Gọi thật** (mode=real, provider=twilio).
   Kiểm tra nhanh: `GET /telephony/status` → `"provider":"twilio"`.
2. Tạo/sửa 1 bệnh nhân có **số điện thoại = 0975261207** (số của bạn).
3. Bấm **📲 Gọi điện** trên dòng bệnh nhân đó.
4. Điện thoại bạn reo → nhấc máy → (nghe lời nhắn trial của Twilio) → nghe câu hỏi
   tiếng Việt (VNPT TTS) → **trả lời** (vd "tôi bị đau ngực và khó thở") → cúp máy.
5. Vài giây sau dashboard tự cập nhật triage + cảnh báo.

## Luồng kỹ thuật
```
POST Calls.json (Twilio)  → máy bạn reo
  TwiML: <Play> câu hỏi VNPT TTS </Play> <Record/>
  → bạn trả lời, Twilio ghi âm
  → POST /telephony/twilio-recording (qua ngrok)
  → tải file ghi âm (Basic auth) → VNPT STT → triage → cảnh báo
```

## Khắc phục sự cố
| Triệu chứng | Xử lý |
|---|---|
| Badge vẫn 🧪 mô phỏng | Thiếu 1 biến `TWILIO_*`, hoặc chưa restart |
| Lỗi 21210 / "not verified" | Số `to` chưa verify (Bước 5) |
| Lỗi 21215 / geo permission | Chưa bật Vietnam (Bước 4) |
| Máy reo, có hỏi, nhưng không ra transcript | ngrok tắt/sai URL → Twilio không POST ghi âm về được |
| Transcript rỗng | Nói rõ 3–10s; file ghi âm quá ngắn/ồn |

> Câu hỏi phát bằng **VNPT TTS** (`/telephony/question.wav`), trả lời hiểu bằng
> **VNPT STT**. Twilio chỉ là đường dây gọi + ghi âm.
