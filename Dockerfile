# CardioCare — image chạy 1 lệnh, không cần cài Python/venv trên máy giám khảo.
FROM python:3.12-slim

WORKDIR /app

# Cài dependencies trước để tận dụng layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1

EXPOSE 8000

# Mặc định chạy server (docker-compose sẽ seed dữ liệu demo trước khi chạy).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
