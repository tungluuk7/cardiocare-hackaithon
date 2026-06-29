# Deploy CardioCare — Render & Railway

Backend là FastAPI thuần (Python 3.12), không cần Docker. Deploy được lên cả
**Render** và **Railway** chỉ với repo GitHub. Các file cấu hình đã có sẵn:

| File | Dùng cho |
|---|---|
| `Procfile` | Lệnh khởi động chung (`uvicorn ... --port $PORT`) |
| `runtime.txt` | Khoá Python 3.12.10 |
| `render.yaml` | Render Blueprint (1-click, kèm danh sách env vars) |
| `railway.json` | Railway (Nixpacks + start command + healthcheck) |
| `.gitignore` | Loại `.env`, `.venv`, `*.db`… khỏi commit |

> App đọc `PORT` từ env (platform tự cấp), `DB_PATH` từ env, và mọi khóa bí mật
> từ env — **không** hardcode. Có sẵn endpoint `GET /health` để healthcheck.

---

## 0. Chuẩn bị: đẩy code lên GitHub

Thư mục này chưa phải git repo. Khởi tạo và push:

```bash
cd cardiocare
git init
git add .
git commit -m "CardioCare backend"
git branch -M main
git remote add origin https://github.com/<user>/cardiocare.git
git push -u origin main
```

`.gitignore` đảm bảo `.env`, `.venv/`, `*.db` **không** bị đẩy lên.

---

## 1. Deploy lên Render (khuyến nghị — có `render.yaml`)

1. Vào https://dashboard.render.com → **New** → **Blueprint**.
2. Chọn repo `cardiocare`. Render đọc `render.yaml`, tự tạo web service.
3. Mở service → tab **Environment** → điền các biến `sync: false`:
   - VNPT: `VNPT_VOICE_TTS_URL`, `VNPT_VOICE_STT_URL`, `VNPT_VOICE_TOKEN_ID`,
     `VNPT_VOICE_TOKEN_KEY`, `VNPT_VOICE_STT_TOKEN_ID`, `VNPT_VOICE_STT_TOKEN_KEY`,
     `VNPT_VOICE_ACCESS_TOKEN`
   - Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
   - Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - (Zalo nếu dùng production)
4. Deploy. Khi xong, Render cấp URL dạng `https://cardiocare.onrender.com`.
5. **Copy URL đó vào biến `PUBLIC_BASE_URL`** rồi **Manual Deploy → Clear cache & deploy**
   (Twilio cần URL này để gọi webhook ghi âm về).
6. Kiểm tra:
   - `https://cardiocare.onrender.com/health` → `{"status":"ok"}`
   - `https://cardiocare.onrender.com/docs` → Swagger
   - `https://cardiocare.onrender.com/static/index.html` → dashboard

### Không dùng Blueprint (thủ công)
New → **Web Service** → chọn repo →
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Thêm env vars như trên.

---

## 2. Deploy lên Railway

1. https://railway.app → **New Project** → **Deploy from GitHub repo** → chọn `cardiocare`.
2. Railway dùng Nixpacks tự nhận Python; `railway.json` cấp sẵn start command + healthcheck.
3. Tab **Variables** → thêm các biến env (VNPT, Twilio, Telegram, `CALL_SCHEDULER_ENABLED=true`).
4. **Settings → Networking → Generate Domain** để lấy URL public.
5. Đặt `PUBLIC_BASE_URL` = URL vừa tạo → redeploy.

---

## 3. Lưu ý về SQLite (quan trọng)

- Free tier của Render/Railway dùng **filesystem tạm** → file `cardiocare.db` **reset
  sau mỗi lần redeploy/restart**. Đủ cho demo, **không** dùng cho dữ liệu thật.
- Muốn giữ dữ liệu:
  - **Render**: nâng plan, bỏ comment block `disk:` trong `render.yaml`
    (mount `/var/data`) và đặt `DB_PATH=/var/data/cardiocare.db`.
  - **Railway**: thêm **Volume**, mount vào 1 thư mục rồi đặt `DB_PATH` trỏ vào đó.
  - Production thật nên chuyển sang **Postgres** (Render/Railway đều cấp sẵn).

---

## 4. Lưu ý vận hành sau deploy

- **Scheduler tự gọi**: chạy ngay khi server lên. Nếu chưa cấu hình Twilio →
  tự chuyển sang **mô phỏng** (dashboard vẫn cập nhật), không crash. Tắt bằng
  `CALL_SCHEDULER_ENABLED=false`.
- **Render free** ngủ sau ~15 phút không có request (cold start chậm lần đầu).
  Scheduler nền có thể giữ tiến trình thức — theo dõi quota free.
- **Twilio trial**: chỉ gọi/nhắn số đã verify. Production cần nâng cấp tài khoản
  (xem `TWILIO_SETUP.md`).
