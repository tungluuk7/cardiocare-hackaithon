import re
import unicodedata
from dataclasses import dataclass
from typing import List


@dataclass
class Symptom:
    id: str             # mã định danh snake_case (key dùng chung Dev 1/Dev 3), vd "dau_nguc"
    name: str           # nhãn tiếng Việt hiển thị, vd "Đau ngực"
    keywords: List[str] # các cách bệnh nhân diễn đạt (lowercase, để matching)
    triage_level: str   # "RED" | "YELLOW"


# ── Sinh biến thể KHÔNG DẤU cho từ khoá ───────────────────────────────────────
# STT/gõ phím đôi khi trả về tiếng Việt không dấu ("dau nguc", "kho tho").
# Ta tự sinh biến thể không dấu từ danh sách có dấu (khỏi phải liệt kê tay).
# Matching so khớp có phân biệt dấu, nên biến thể không dấu chỉ khớp văn bản
# không dấu — không ảnh hưởng nhận diện văn bản có dấu.
#
# _ACCENT_FREE_DENY: những dạng không dấu 1-từ dễ TRÙNG nghĩa với từ khác
# (dương tính giả) nên KHÔNG tự sinh:
#   xiu  ← "xỉu"  trùng "xíu" (một xíu)
#   non  ← "nôn"  trùng "non" (còn non)
#   oi   ← "ói"   trùng chuỗi con trong "nói", "rồi"
#   ho   ← phòng xa (trùng chuỗi con trong "cho", "nhỏ")
_ACCENT_FREE_DENY = {"xiu", "non", "oi", "ho"}


def _strip_accents(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _kw(keywords: List[str]) -> List[str]:
    """Trả về danh sách từ khoá + biến thể không dấu (bỏ dạng dễ nhầm)."""
    out = list(keywords)
    for k in keywords:
        naf = _strip_accents(k)
        if naf != k and naf not in _ACCENT_FREE_DENY and naf not in out:
            out.append(naf)
    return out


# ── Nhóm RED — triệu chứng khẩn cấp ───────────────────────────────────────────
# Cơ sở: bệnh nhân sau can thiệp mạch vành (PCI/đặt stent) dùng thuốc kháng kết
# tập tiểu cầu kép → nguy cơ HUYẾT KHỐI trong stent (đau ngực, nhồi máu lại) và
# XUẤT HUYẾT (do thuốc). Kèm nguy cơ ĐỘT QUỴ do huyết khối.
RED_SYMPTOMS: List[Symptom] = [
    Symptom(
        id="dau_nguc",
        name="Đau ngực",
        keywords=_kw([
            "đau ngực", "tức ngực", "đau tim", "thắt ngực", "nặng ngực",
            "đau ở ngực", "ngực đau", "ngực tức", "đau vùng ngực",
            "đau thắt ngực", "đau lan cánh tay", "đau lan ra tay",
            "đau ra sau lưng", "đau lan lên hàm",
        ]),
        triage_level="RED",
    ),
    Symptom(
        id="ngat",
        name="Ngất",
        keywords=_kw([
            "ngất", "mất ý thức", "bất tỉnh", "xỉu", "ngã xỉu",
            "ngất xỉu", "ngất đi", "mê man", "lịm đi", "gục xuống",
        ]),
        triage_level="RED",
    ),
    Symptom(
        id="chay_mau",
        name="Chảy máu vết thương",
        keywords=_kw([
            "chảy máu", "máu chảy", "vết thương chảy máu", "máu nhiều",
            "mất máu", "chảy máu không cầm", "rỉ máu vết mổ", "chảy máu vết mổ",
        ]),
        triage_level="RED",
    ),
    Symptom(
        id="xuat_huyet",
        name="Xuất huyết bất thường",
        keywords=_kw([
            "xuất huyết", "đi ngoài phân đen", "đại tiện phân đen", "phân đen",
            "nôn ra máu", "ói ra máu", "tiểu ra máu", "đi tiểu ra máu",
            "chảy máu cam", "chảy máu chân răng", "chảy máu lợi",
            "bầm tím nhiều", "xuất huyết dưới da",
        ]),
        triage_level="RED",
    ),
    Symptom(
        id="dau_hieu_dot_quy",
        name="Dấu hiệu đột quỵ",
        keywords=_kw([
            "đột quỵ", "méo miệng", "méo mồm", "yếu nửa người", "liệt nửa người",
            "tê nửa người", "tê tay chân", "tay chân yếu", "nói khó", "nói ngọng",
            "cứng lưỡi", "mắt mờ đột ngột",
        ]),
        triage_level="RED",
    ),
]

# ── Nhóm YELLOW — triệu chứng cần theo dõi ────────────────────────────────────
# Cơ sở: dấu hiệu SUY TIM (khó thở, phù, mệt), RỐI LOẠN NHỊP (hồi hộp), tụt/tăng
# huyết áp (chóng mặt), nhiễm trùng (sốt), tác dụng phụ thuốc (buồn nôn).
YELLOW_SYMPTOMS: List[Symptom] = [
    Symptom(
        id="kho_tho",
        name="Khó thở",
        keywords=_kw([
            "khó thở", "thở khó", "thở không được", "hụt hơi", "thiếu hơi",
            "thở yếu", "thở nặng", "thở gấp", "ngột ngạt",
            "khó thở khi nằm", "khó thở về đêm", "nằm khó thở",
        ]),
        triage_level="YELLOW",
    ),
    Symptom(
        id="chong_mat",
        name="Chóng mặt",
        keywords=_kw([
            "chóng mặt", "hoa mắt", "váng đầu", "xây xẩm",
            "quay cuồng", "đầu váng", "choáng váng",
        ]),
        triage_level="YELLOW",
    ),
    Symptom(
        id="phu_chan",
        name="Phù chân",
        keywords=_kw([
            "phù chân", "sưng chân", "chân sưng", "phù nề", "chân to hơn",
            "chân bị sưng", "sưng phù", "bàn chân sưng", "phù mặt",
            "phù toàn thân", "mắt cá sưng",
        ]),
        triage_level="YELLOW",
    ),
    Symptom(
        id="hoi_hop",
        name="Hồi hộp",
        keywords=_kw([
            "hồi hộp", "tim đập nhanh", "tim đập mạnh", "loạn nhịp",
            "đánh trống ngực", "tim loạn", "nhịp tim bất thường",
            "tim đập thình thịch",
        ]),
        triage_level="YELLOW",
    ),
    Symptom(
        id="sot",
        name="Sốt",
        keywords=_kw([
            "sốt", "nóng sốt", "nhiệt độ cao", "nóng người",
            "sốt cao", "hâm hấp", "người hâm hấp",
        ]),
        triage_level="YELLOW",
    ),
    Symptom(
        id="met_moi",
        name="Mệt mỏi",
        keywords=_kw([
            "mệt", "mệt mỏi", "uể oải", "kiệt sức", "yếu sức",
            "đuối sức", "rã rời", "mệt nhiều",
        ]),
        triage_level="YELLOW",
    ),
    Symptom(
        id="buon_non",
        name="Buồn nôn / Nôn",
        keywords=_kw([
            "buồn nôn", "nôn", "nôn ói", "nôn mửa", "buồn ói",
            "nôn nao", "ói mửa",
        ]),
        triage_level="YELLOW",
    ),
]

ALL_SYMPTOMS: List[Symptom] = RED_SYMPTOMS + YELLOW_SYMPTOMS

# Map ID → nhãn tiếng Việt hiển thị. Dev 1/Dev 3 dùng để render label cho người đọc.
# vd SYMPTOM_LABELS["kho_tho"] == "Khó thở"
SYMPTOM_LABELS = {s.id: s.name for s in ALL_SYMPTOMS}

# Token phủ định (so khớp theo từ, không theo chuỗi con — tránh lỗi " k " thiếu space).
# Gồm cả biến thể không dấu vì STT đôi khi trả về không dấu.
NEGATION_TOKENS = {
    "không", "khong", "chưa", "chua", "chẳng", "chang",
    "ko", "k", "đừng", "dung", "hết", "het",
}

# Giữ lại để tương thích ngược cho code cũ còn import (đã thay bằng NEGATION_TOKENS).
NEGATION_WORDS: List[str] = sorted(NEGATION_TOKENS)

# Ranh giới mệnh đề: dấu câu + liên từ chuyển ý/đối lập.
# Phủ định ở mệnh đề trước KHÔNG được lan sang mệnh đề sau.
_CLAUSE_SPLIT_RE = re.compile(
    r"[.,;!?\n]+"
    r"|\b(?:nhưng|mà|rồi|giờ|bây giờ|nay|lại|còn|song|tuy nhiên)\b"
)

# Tách token để dò phủ định (\w trong Python 3 đã bắt được chữ tiếng Việt có dấu).
_WORD_RE = re.compile(r"\w+", re.UNICODE)

TRIAGE_MESSAGES = {
    "RED":    "KHẨN CẤP: Phát hiện triệu chứng nguy hiểm. Cần can thiệp ngay!",
    "YELLOW": "THEO DÕI: Cần thông báo điều dưỡng và theo dõi sát bệnh nhân.",
    "GREEN":  "BÌNH THƯỜNG: Không phát hiện triệu chứng nguy hiểm.",
}


# ── Nhận diện triệu chứng (logic dùng chung cho triage_engine + smartbot_ner) ──

def _split_clauses(text: str) -> List[str]:
    """Tách text (đã lowercase) thành các mệnh đề theo dấu câu + liên từ chuyển ý."""
    clauses = [c.strip() for c in _CLAUSE_SPLIT_RE.split(text) if c and c.strip()]
    return clauses or [text]


def _clause_has_symptom(clause: str, keywords: List[str]) -> bool:
    """
    True nếu trong mệnh đề có keyword KHÔNG bị phủ định.

    Quy tắc phủ định tiếng Việt: token phủ định ('không', 'chưa'...) đứng TRƯỚC
    keyword trong cùng mệnh đề thì mới triệt tiêu. Duyệt mọi lần xuất hiện —
    chỉ cần 1 lần dương tính là tính có triệu chứng.
    """
    for kw in keywords:
        start = 0
        while True:
            pos = clause.find(kw, start)
            if pos == -1:
                break
            tokens_before = _WORD_RE.findall(clause[:pos])
            if not any(tok in NEGATION_TOKENS for tok in tokens_before):
                return True
            start = pos + len(kw)
    return False


def match_symptoms(text: str) -> List[str]:
    """
    Trả về danh sách ID triệu chứng phát hiện trong text (vd ["dau_nguc", "ngat"]).
    Thứ tự ưu tiên RED trước YELLOW (theo thứ tự ALL_SYMPTOMS), không trùng lặp.
    """
    clauses = _split_clauses(text.lower())
    found: List[str] = []
    for symptom in ALL_SYMPTOMS:
        if any(_clause_has_symptom(c, symptom.keywords) for c in clauses):
            found.append(symptom.id)
    return found
