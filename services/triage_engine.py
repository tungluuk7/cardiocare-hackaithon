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
    match_symptoms,
)

logger = logging.getLogger("cardiocare.triage")

# Chỉ log "Smartbot chưa cấu hình" một lần để tránh spam mỗi request.
_smartbot_unconfigured_logged = False


@dataclass
class TriageResult:
    level: str                  # "RED" | "YELLOW" | "GREEN"
    symptoms: List[str]         # tên chuẩn, vd ["đau ngực", "ngất"]
    message: str                # chuỗi khuyến nghị
    symptom_labels: List[str]   # nhãn hiển thị cho UI/alert, vd ["Đau ngực", "Ngất"]


def _to_label(name: str) -> str:
    """Viết hoa chữ cái đầu để hiển thị đẹp: 'đau ngực' → 'Đau ngực'."""
    return name[:1].upper() + name[1:] if name else name



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

    level = _determine_level(found)

    return TriageResult(
        level=level,
        symptoms=found,
        symptom_labels=[_to_label(s) for s in found],
        message=TRIAGE_MESSAGES[level],
    )


# ── Keyword matching (fallback) ───────────────────────────────────────────────

def _keyword_match(transcript: str) -> List[str]:
    """
    Fallback khi không gọi được Smartbot: nhận diện triệu chứng bằng
    matching theo mệnh đề + xử lý phủ định (logic chung ở symptom_schema).
    """
    return match_symptoms(transcript)


def _determine_level(symptoms: List[str]) -> str:
    red_names   = {s.name for s in RED_SYMPTOMS}
    yellow_names = {s.name for s in YELLOW_SYMPTOMS}

    if any(s in red_names for s in symptoms):
        return "RED"
    if any(s in yellow_names for s in symptoms):
        return "YELLOW"
    return "GREEN"
