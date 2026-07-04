"""
OCR endpoint — số hoá giấy ra viện để tạo NHÁP hồ sơ bệnh nhân.

  GET  /ocr/status              → {enabled}  (frontend ẩn/hiện nút upload)
  POST /ocr/discharge (file)    → {ok, draft, raw_lines}

QUAN TRỌNG (an toàn y tế): endpoint chỉ TRẢ BẢN NHÁP, KHÔNG tự ghi DB.
Điều dưỡng xem/sửa trên form rồi mới bấm tạo qua POST /patients (human-in-the-loop).
"""
from fastapi import APIRouter, UploadFile, File
from services.vnpt_ocr import ocr_ready, ocr_lines, parse_discharge

router = APIRouter(prefix="/ocr", tags=["ocr"])

# Giới hạn kích thước file để tránh nuốt ảnh quá lớn (10MB đủ cho giấy tờ).
_MAX_BYTES = 10 * 1024 * 1024


@router.get("/status")
def ocr_status():
    return {"enabled": ocr_ready()}


@router.post("/discharge")
async def ocr_discharge(file: UploadFile = File(...)):
    if not ocr_ready():
        return {"ok": False, "reason": "SmartReader chưa cấu hình (thiếu Token-id/Token-key)."}

    data = await file.read()
    if not data:
        return {"ok": False, "reason": "File rỗng."}
    if len(data) > _MAX_BYTES:
        return {"ok": False, "reason": "File quá lớn (tối đa 10MB)."}

    try:
        lines = await ocr_lines(data, file.filename or "discharge.pdf")
    except Exception as e:
        # Chỉ lộ tên loại lỗi, không lộ chi tiết nội bộ.
        return {"ok": False, "reason": f"OCR lỗi ({type(e).__name__}). Thử lại hoặc nhập tay."}

    if not lines:
        return {"ok": False, "reason": "Không đọc được chữ từ ảnh. Chụp rõ hơn hoặc nhập tay."}

    return {"ok": True, "draft": parse_discharge(lines), "raw_lines": lines}
