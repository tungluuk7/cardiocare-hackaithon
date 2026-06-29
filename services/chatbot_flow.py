"""
Chatbot flow — sinh câu trả lời tự nhiên cho cửa sổ chat hỏi thăm bệnh nhân.

Dev 1 (api/chatbot.py) dùng:
    from services.chatbot_flow import generate_reply, get_opening_question
    reply = generate_reply(symptom_ids, level, turn)   # symptom_ids = ["dau_nguc", ...]
    opening = get_opening_question(0)

Triết lý: nói chuyện như điều dưỡng thật hỏi thăm cụ già — xưng "cháu", gọi "bác",
nhẹ nhàng, không cứng nhắc kiểu máy. RED thì trấn an + thúc giục xử lý ngay.
"""

from services.symptom_schema import SYMPTOM_LABELS

# ── Câu hỏi mở đầu: hỏi thăm tuần tự khi CHƯA phát hiện triệu chứng nguy hiểm ──
OPENING_QUESTIONS = [
    "Cháu chào bác ạ! Cháu là trợ lý CardioCare, gọi hỏi thăm sức khỏe bác hôm nay. "
    "Bác thấy trong người thế nào ạ?",
    "Dạ vâng ạ. Mấy hôm nay bác có thấy tức ngực, khó thở hay mệt vùng ngực gì không ạ?",
    "Bác ăn uống, ngủ nghỉ có ổn không ạ? Có thấy chóng mặt hay hồi hộp gì không bác?",
    "Chân tay bác có bị sưng phù hay nặng nề gì không ạ?",
]

# ── Câu hỏi đào sâu riêng cho từng triệu chứng (theo ID) ──────────────────────
SYMPTOM_FOLLOWUPS = {
    "dau_nguc":  "Cơn đau ngực của bác có lan ra cánh tay trái, vai hay sau lưng không ạ? "
                 "Bác đau lâu chưa?",
    "ngat":      "Lúc bác bị ngất có ai bên cạnh không, và bác tỉnh lại sau bao lâu ạ?",
    "chay_mau":  "Vết chảy máu của bác ở đâu ạ, và hiện có cầm được chưa?",
    "kho_tho":   "Bác khó thở cả lúc ngồi nghỉ hay chỉ khi đi lại, gắng sức ạ?",
    "chong_mat": "Bác chóng mặt có kèm buồn nôn hay đứng không vững không ạ?",
    "phu_chan":  "Chân bác sưng một bên hay cả hai bên ạ? Ấn vào có để lại vết lõm không bác?",
    "hoi_hop":   "Tim bác đập nhanh từng cơn hay liên tục ạ? Có kèm đau ngực không bác?",
    "sot":       "Bác sốt mấy hôm rồi ạ, và người có gai rét hay đau mỏi gì không?",
}


def get_opening_question(index: int) -> str:
    """Lấy câu hỏi mở đầu thứ `index`. Vượt quá danh sách → câu chốt thân thiện."""
    if 0 <= index < len(OPENING_QUESTIONS):
        return OPENING_QUESTIONS[index]
    return ("Dạ bác giữ gìn sức khỏe nhé. Có gì bất thường bác nhắn cháu ngay ạ. "
            "Cháu chào bác ạ!")


def _labels(symptom_ids) -> str:
    """Gộp nhãn tiếng Việt từ danh sách ID, vd ['dau_nguc'] → 'Đau ngực'."""
    names = [SYMPTOM_LABELS[s] for s in symptom_ids if s in SYMPTOM_LABELS]
    return ", ".join(name.lower() for name in names)


def generate_reply(symptom_ids, level: str, turn: int) -> str:
    """
    Sinh câu trả lời theo tình huống.

    symptom_ids : danh sách ID triệu chứng ĐÃ CỘNG DỒN qua các turn (vd ["dau_nguc"])
    level       : "RED" | "YELLOW" | "GREEN"
    turn        : số thứ tự lượt hiện tại (0-based, trước khi tăng)
    """
    # RED — khẩn cấp: trấn an + thúc giục, KHÔNG hỏi lan man nữa
    if level == "RED":
        syms = _labels(symptom_ids) or "dấu hiệu nguy hiểm"
        return (
            f"Bác ơi, bác đang có {syms} — đây là dấu hiệu cần xử lý NGAY ạ. "
            "Cháu sẽ báo điều dưỡng và người nhà liên hệ với bác ngay bây giờ. "
            "Bác cố gắng ngồi hoặc nằm nghỉ, hít thở chậm, đừng gắng sức bác nhé. "
            "Nếu thấy nặng hơn, bác hoặc người nhà gọi 115 ngay ạ!"
        )

    # YELLOW — cần theo dõi: ghi nhận + hỏi đào sâu triệu chứng
    if level == "YELLOW":
        syms = _labels(symptom_ids)
        followup = next(
            (SYMPTOM_FOLLOWUPS[s] for s in symptom_ids if s in SYMPTOM_FOLLOWUPS),
            "Tình trạng này bác bị bao lâu rồi ạ?",
        )
        return (
            f"Dạ cháu ghi nhận bác có {syms} ạ. Cái này mình cần theo dõi thêm. "
            f"{followup}"
        )

    # GREEN — chưa có gì nguy hiểm: tiếp tục hỏi thăm nhẹ nhàng
    next_q = get_opening_question(turn + 1)
    return f"Dạ vâng, nghe bác khỏe cháu mừng ạ. {next_q}"


# ── Mẫu thông báo cảnh báo cho bệnh nhân (TTS/email khi RED phát hiện qua chat) ──

def build_patient_alert(patient_name: str, symptom_ids, level: str) -> str:
    """Nội dung nhắn/đọc cho bệnh nhân & người nhà khi chat phát hiện RED/YELLOW."""
    syms = _labels(symptom_ids) or "dấu hiệu bất thường"
    if level == "RED":
        return (
            f"CardioCare xin thông báo: bác {patient_name} vừa báo có {syms} qua hệ thống "
            f"hỏi thăm. Đây là dấu hiệu khẩn cấp, đề nghị người nhà liên hệ và đưa bác đi "
            f"khám ngay. Gọi 115 nếu cần hỗ trợ y tế khẩn cấp."
        )
    return (
        f"CardioCare thông báo: bác {patient_name} có {syms} cần theo dõi. "
        f"Đề nghị điều dưỡng/người nhà quan tâm và liên hệ lại với bác trong hôm nay."
    )
