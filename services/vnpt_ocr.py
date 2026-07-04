"""
OCR service — số hoá giấy tờ y tế qua VNPT SmartReader (api.idg.vnpt.vn).

Luồng 2 bước (theo "Tài liệu API số hoá văn bản (Cơ bản)" + Postman Hackathon):
  1) POST /file-service/v1/addFile           (multipart file)  → object.hash
  2) POST /rpa-service/aidigdoc/v1/ocr/scan  (json)            → object.lines/phrases

Header bắt buộc: Authorization (Bearer access_token), Token-id, Token-key, mac-address.
Token-id/Token-key của SmartReader KHÁC SmartVoice; access_token dùng chung cho
các dịch vụ trên api.idg.vnpt.vn.

Phase 1: OCR giấy RA VIỆN → text thô → parse_discharge() bóc ra bản NHÁP hồ sơ
bệnh nhân (điều dưỡng xem/sửa rồi mới lưu — human-in-the-loop).
"""
import re
import uuid
import httpx
from config import settings

_BASE = settings.VNPT_VOICE_BASE_URL          # https://api.idg.vnpt.vn
_MAC = "EGOV-DIGDOC-WEB-API"                   # giá trị mac-address theo Postman


class OcrError(Exception):
    """Lỗi từ SmartReader, giữ lại bước + HTTP status + body để chẩn đoán."""
    def __init__(self, step: str, status: int, body: str):
        self.step, self.status, self.body = step, status, body
        super().__init__(f"{step} HTTP {status}: {body[:300]}")

    def short(self) -> str:
        """Trích message VNPT nếu có, không thì cắt gọn body."""
        import json as _json
        try:
            j = _json.loads(self.body)
            msg = j.get("message") or j.get("error") or j.get("error_description")
            if msg:
                return str(msg)
        except Exception:
            pass
        return (self.body or "").strip()[:160] or "(không có nội dung)"


def ocr_ready() -> bool:
    """Có đủ credentials để gọi SmartReader không."""
    return bool(settings.SMARTREADER_TOKEN_ID and settings.SMARTREADER_ACCESS_TOKEN)


def _bearer(tok: str) -> str:
    """VNPT yêu cầu 'Bearer <access_token>'. Tự thêm nếu người dùng dán token thô."""
    tok = (tok or "").strip()
    if tok and not tok.lower().startswith("bearer "):
        tok = "Bearer " + tok
    return tok


def _auth_headers(json: bool = True) -> dict:
    h = {
        "Authorization": _bearer(settings.SMARTREADER_ACCESS_TOKEN),
        "Token-id":      settings.SMARTREADER_TOKEN_ID,
        "Token-key":     settings.SMARTREADER_TOKEN_KEY,
        "mac-address":   _MAC,
    }
    if json:
        h["Content-Type"] = "application/json"
    return h


# ── Gọi VNPT SmartReader ──────────────────────────────────────────────────────

async def ocr_lines(file_bytes: bytes, filename: str) -> list[str]:
    """
    Số hoá 1 file (ảnh/PDF) → danh sách dòng text (gộp mọi trang).
    Ném exception nếu VNPT trả lỗi — caller quyết định xử lý.
    """
    async with httpx.AsyncClient(timeout=120) as client:
        # B1: upload lấy hash
        add = await client.post(
            f"{_BASE}/file-service/v1/addFile",
            files={"file": (filename, file_bytes)},
            data={"title": "cardiocare-doc", "description": "medical document"},
            headers=_auth_headers(json=False),
        )
        if add.status_code >= 400:
            raise OcrError("addFile", add.status_code, add.text)
        obj = add.json().get("object", {})
        file_hash = obj.get("hash")
        file_type = obj.get("fileType") or _guess_type(filename)
        if not file_hash:
            raise OcrError("addFile", add.status_code, add.text)

        # B2: OCR text thuần
        scan = await client.post(
            f"{_BASE}/rpa-service/aidigdoc/v1/ocr/scan",
            json={
                "file_hash":      file_hash,
                "file_type":      file_type,
                "token":          f"cardiocare-{uuid.uuid4().hex[:12]}",
                "client_session": str(uuid.uuid4()),
                "details":        False,
            },
            headers=_auth_headers(json=True),
        )
        if scan.status_code >= 400:
            raise OcrError("ocr/scan", scan.status_code, scan.text)
        return _flatten_lines(scan.json().get("object", {}))


def _guess_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    return "pdf" if ext == "pdf" else ext          # jpg/png/... hoặc pdf


def _flatten_lines(obj: dict) -> list[str]:
    """object.lines là list theo trang, mỗi trang là list dòng → gộp phẳng."""
    out: list[str] = []
    for page in obj.get("lines") or []:
        if isinstance(page, list):
            out.extend(s.strip() for s in page if isinstance(s, str) and s.strip())
        elif isinstance(page, str) and page.strip():
            out.append(page.strip())
    return out


# ── Bóc tách giấy RA VIỆN → bản nháp hồ sơ ────────────────────────────────────
# Rule-based (deterministic, không tốn thêm API). Vì là bản nháp cho điều dưỡng
# duyệt nên fuzzy chấp nhận được; bước sau có thể thay bằng LLM Smartbot.

# Nhãn → tên trường. Mỗi trường thử nhiều biến thể nhãn hay gặp trên giấy ra viện.
_LABELS = {
    "name":           [r"họ và tên", r"họ tên", r"người bệnh", r"tên người bệnh"],
    "age":            [r"tuổi"],
    "birth":          [r"năm sinh", r"ngày sinh", r"sinh ngày"],
    "pid":            [r"mã bệnh nhân", r"mã bn", r"số bệnh án", r"mã y tế", r"mã hồ sơ", r"pid"],
    "diagnosis":      [r"chẩn đoán ra viện", r"chẩn đoán khi ra viện", r"chẩn đoán"],
    "discharge_date": [r"ngày ra viện", r"ngày xuất viện", r"ra viện hồi", r"ra viện lúc"],
    "doctor":         [r"bác sĩ điều trị", r"bs điều trị", r"bác sỹ điều trị", r"bác sĩ", r"bác sỹ"],
}


def parse_discharge(lines: list[str]) -> dict:
    """
    Từ các dòng OCR → bản nháp: name, age, doctor_name, discharge_date, diagnosis, pid.
    Trường không tìm thấy để rỗng (điều dưỡng tự điền).
    """
    draft = {"name": "", "age": None, "doctor_name": "",
             "discharge_date": "", "diagnosis": "", "pid": ""}

    draft["name"]           = _value_for(_LABELS["name"], lines)
    draft["doctor_name"]    = _value_for(_LABELS["doctor"], lines)
    draft["diagnosis"]      = _value_for(_LABELS["diagnosis"], lines)
    draft["pid"]            = _value_for(_LABELS["pid"], lines)
    draft["discharge_date"] = _norm_date(_value_for(_LABELS["discharge_date"], lines))

    age = _value_for(_LABELS["age"], lines)
    m = re.search(r"\d{1,3}", age or "")
    if m:
        draft["age"] = int(m.group())
    else:
        # suy ra tuổi từ năm sinh nếu có
        birth = _value_for(_LABELS["birth"], lines)
        by = re.search(r"(19|20)\d{2}", birth or "")
        if by:
            from config import now_vn
            draft["age"] = max(0, now_vn().year - int(by.group()))

    return draft


# Ranh giới cắt giá trị: gặp trường KẾ dính chung dòng thì dừng.
_FIELD_BOUNDARY = r"\s{2,}|giới tính|số thẻ|tổng số ngày|mã bệnh|ngày sinh|khoa\b"


def _value_for(label_patterns: list[str], lines: list[str]) -> str:
    """
    Bóc giá trị của trường theo nhãn.

    - Ưu tiên NHÃN CỤ THỂ trước (duyệt từng pattern qua mọi dòng) để nhãn phụ
      trên dòng khác không cướp mất (vd "Lời dặn của bác sĩ:" không được nhận là
      "Bác sĩ điều trị").
    - Giá trị lấy SAU dấu ':' đứng sau nhãn (form VN dạng "Nhãn ...: giá trị"),
      cắt ở ranh giới trường kế tiếp. Nhãn đứng một mình (heading) → lấy dòng kế.
    """
    for pat in label_patterns:
        for i, line in enumerate(lines):
            m = re.search(pat, line.lower())
            if not m:
                continue
            rest = line[m.end():]
            cm = re.search(r":", rest)          # giá trị nằm sau dấu ':' sau nhãn
            val = rest[cm.end():] if cm else rest
            val = re.sub(r"^\s*[:\-–]\s*", "", val).strip()
            val = re.split(_FIELD_BOUNDARY, val, maxsplit=1, flags=re.I)[0].strip()
            if val:
                return val
            if i + 1 < len(lines):              # nhãn là heading → giá trị ở dòng dưới
                return lines[i + 1].strip()
    return ""


def _norm_date(raw: str) -> str:
    """Chuẩn hoá ngày về YYYY-MM-DD nếu nhận diện được; không thì trả lại thô."""
    if not raw:
        return ""
    m = re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})", raw)
    if not m:
        m = re.search(r"ngày\s*(\d{1,2}).*?tháng\s*(\d{1,2}).*?năm\s*(\d{4})", raw, re.I)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            return f"{y:04d}-{mo:02d}-{d:02d}"
    return raw.strip()
