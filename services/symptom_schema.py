import re
from dataclasses import dataclass
from typing import List


@dataclass
class Symptom:
    name: str
    keywords: List[str]
    triage_level: str  

RED_SYMPTOMS: List[Symptom] = [
    Symptom(
        name="đau ngực",
        keywords=[
            "đau ngực", "tức ngực", "đau tim", "thắt ngực", "nặng ngực",
            "đau ở ngực", "ngực đau", "ngực tức", "đau vùng ngực",
        ],
        triage_level="RED",
    ),
    Symptom(
        name="ngất",
        keywords=[
            "ngất", "mất ý thức", "bất tỉnh", "xỉu", "ngã xỉu",
            "ngất xỉu", "ngất đi", "mê man",
        ],
        triage_level="RED",
    ),
    Symptom(
        name="chảy máu vết thương",
        keywords=[
            "chảy máu", "xuất huyết", "máu chảy", "vết thương chảy máu",
            "máu nhiều", "mất máu",
        ],
        triage_level="RED",
    ),
]

YELLOW_SYMPTOMS: List[Symptom] = [
    Symptom(
        name="khó thở",
        keywords=[
            "khó thở", "thở khó", "thở không được", "hụt hơi",
            "thiếu hơi", "thở yếu", "thở nặng",
        ],
        triage_level="YELLOW",
    ),
    Symptom(
        name="chóng mặt",
        keywords=[
            "chóng mặt", "hoa mắt", "váng đầu", "xây xẩm",
            "quay cuồng", "đầu váng",
        ],
        triage_level="YELLOW",
    ),
    Symptom(
        name="phù chân",
        keywords=[
            "phù chân", "sưng chân", "chân sưng", "phù nề",
            "chân to hơn", "chân bị sưng", "hơi sưng", "bị sưng",
        ],
        triage_level="YELLOW",
    ),
    Symptom(
        name="hồi hộp",
        keywords=[
            "hồi hộp", "tim đập nhanh", "tim đập mạnh",
            "loạn nhịp", "đánh trống ngực",
        ],
        triage_level="YELLOW",
    ),
    Symptom(
        name="sốt",
        keywords=[
            "sốt", "nóng sốt", "nhiệt độ cao", "nóng người", "sốt cao",
        ],
        triage_level="YELLOW",
    ),
]

ALL_SYMPTOMS: List[Symptom] = RED_SYMPTOMS + YELLOW_SYMPTOMS

# Token phủ định (so khớp theo từ, không theo chuỗi con — tránh lỗi " k " thiếu space).
# Gồm cả biến thể không dấu vì STT đôi khi trả về không dấu.
NEGATION_TOKENS = {
    "không", "khong", "chưa", "chua", "chẳng", "chang",
    "ko", "k", "đừng", "dung",
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
    Trả về danh sách tên triệu chứng phát hiện trong text.
    Thứ tự ưu tiên RED trước YELLOW (theo thứ tự ALL_SYMPTOMS), không trùng lặp.
    """
    clauses = _split_clauses(text.lower())
    found: List[str] = []
    for symptom in ALL_SYMPTOMS:
        if any(_clause_has_symptom(c, symptom.keywords) for c in clauses):
            found.append(symptom.name)
    return found
