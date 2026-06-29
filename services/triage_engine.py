"""
Triage Engine — logic cốt lõi của CardioCare.

Dev 1 dùng:
    from services.triage_engine import analyze
    result = await analyze(transcript)
    # result.level  → "RED" | "YELLOW" | "GREEN"
    # result.symptoms → ["đau ngực", "ngất"]
    # result.message  → chuỗi thông báo
"""

import logging
from dataclasses import dataclass
from typing import List

from services.symptom_schema import (
    RED_SYMPTOMS,
    YELLOW_SYMPTOMS,
    TRIAGE_MESSAGES,
    SYMPTOM_LABELS,
    match_symptoms,
)

logger = logging.getLogger("cardiocare.triage")

# Tập ID theo mức độ (dùng để phân loại nhanh)
_RED_IDS    = {s.id for s in RED_SYMPTOMS}
_YELLOW_IDS = {s.id for s in YELLOW_SYMPTOMS}

# Chỉ log "Smartbot chưa cấu hình" một lần để tránh spam mỗi request.
_smartbot_unconfigured_logged = False


@dataclass
class TriageResult:
    level: str                  # "RED" | "YELLOW" | "GREEN"
    symptoms: List[str]         # ID triệu chứng, vd ["dau_nguc", "ngat"]
    message: str                # chuỗi khuyến nghị
    symptom_labels: List[str]   # nhãn hiển thị, vd ["Đau ngực", "Ngất"]



async def analyze(transcript: str) -> TriageResult:
    """
    Phân tích transcript → trả TriageResult.
    Ưu tiên Smartbot NER; nếu API chưa cấu hình/lỗi → dùng keyword fallback.
    """
    global _smartbot_unconfigured_logged
    try:
        from services.smartbot_ner import extract_symptoms_ner
        found = await extract_symptoms_ner(transcript)
    except ValueError:
        # Smartbot chưa cấu hình trong .env → keyword matching (fallback có chủ đích).
        # Log INFO 1 lần thay vì WARN mỗi request.
        if not _smartbot_unconfigured_logged:
            logger.info("Smartbot chua cau hinh — dung keyword matching.")
            _smartbot_unconfigured_logged = True
        found = _keyword_match(transcript)
    except Exception as exc:
        # Lỗi thật khi gọi Smartbot (mạng / HTTP / parse) → cảnh báo (chỉ tên loại lỗi).
        logger.warning("Smartbot loi (%s) — fallback keyword matching.", type(exc).__name__)
        found = _keyword_match(transcript)

    level = _classify(found)

    return TriageResult(
        level=level,
        symptoms=found,
        symptom_labels=[SYMPTOM_LABELS[s] for s in found if s in SYMPTOM_LABELS],
        message=TRIAGE_MESSAGES[level],
    )


# ── Keyword matching (fallback) ───────────────────────────────────────────────

def _keyword_match(transcript: str) -> List[str]:
    """
    Fallback khi không gọi được Smartbot: nhận diện triệu chứng bằng
    matching theo mệnh đề + xử lý phủ định (logic chung ở symptom_schema).
    """
    return match_symptoms(transcript)


def _classify(symptoms: List[str]) -> str:
    """Phân loại mức độ từ danh sách ID triệu chứng. Bất kỳ RED → RED; có YELLOW → YELLOW."""
    if any(s in _RED_IDS for s in symptoms):
        return "RED"
    if any(s in _YELLOW_IDS for s in symptoms):
        return "YELLOW"
    return "GREEN"


# Alias tương thích ngược (code cũ có thể gọi _determine_level)
_determine_level = _classify
