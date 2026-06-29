"""
Alert service: email (nếu SMTP cấu hình được) + in-app alert lưu DB (luôn hoạt động).
GREEN calls không gửi alert.
"""
import smtplib
import json
import sqlite3
from email.mime.text import MIMEText
from datetime import datetime
from config import settings
from services import zalo, telegram


def send_alert(patient_name: str, phone: str, level: str,
               symptom_labels: list[str], message: str,
               patient_id: int = 0) -> bool:
    if level == "GREEN":
        return False

    # Luôn lưu in-app alert vào DB (hiển thị trên dashboard, không cần mạng)
    _save_inapp_alert(patient_id, patient_name, level, symptom_labels, message)

    # RED: báo người thân (YELLOW chỉ lưu DB)
    if level == "RED" and patient_id:
        _notify_family(patient_id, patient_name, symptom_labels)

    # Thử gửi email nếu SMTP đã cấu hình
    if settings.SMTP_PASSWORD and settings.SMTP_USER:
        subject = f"[CardioCare] {level} — Bệnh nhân {patient_name}"
        body = (
            f"Bệnh nhân : {patient_name}\n"
            f"SĐT       : {phone}\n"
            f"Mức độ    : {level}\n"
            f"Triệu chứng: {', '.join(symptom_labels) or 'Không rõ'}\n\n"
            f"{message}"
        )
        if _send_email(subject, body):
            return True

    # Email không gửi được — in-app alert vẫn hoạt động, trả True
    print(f"[alert] In-app alert đã lưu: {level} — {patient_name}")
    return True


def _save_inapp_alert(patient_id: int, patient_name: str, level: str,
                      symptom_labels: list[str], message: str):
    """Lưu alert vào bảng alerts để dashboard hiển thị real-time."""
    try:
        conn = sqlite3.connect(settings.DB_PATH)
        conn.execute(
            "INSERT INTO alerts (patient_id, patient_name, level, symptoms, message) VALUES (?,?,?,?,?)",
            (patient_id, patient_name, level,
             json.dumps(symptom_labels, ensure_ascii=False), message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[alert] Lưu in-app alert thất bại: {e}")


def _notify_family(patient_id: int, patient_name: str, symptom_labels: list[str]):
    """
    RED → báo người thân. Ưu tiên kênh khả dụng:
      1. Zalo ZNS   (cần OA + template + family_phone)
      2. Telegram   (miễn phí, không cần family_phone — kênh chính hiện tại)
      3. SMS Twilio (cần family_phone — VN thường bị gate)
      4. Mô phỏng   (log) nếu chưa cấu hình kênh nào
    """
    try:
        conn = sqlite3.connect(settings.DB_PATH)
        row = conn.execute(
            "SELECT family_phone FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        conn.close()
    except Exception as e:
        print(f"[alert] Đọc family_phone lỗi: {e}")
        row = None

    family_phone = row[0] if row else None
    syms = ", ".join(symptom_labels) or "triệu chứng nguy hiểm"
    thoi_gian = datetime.now().strftime("%H:%M %d/%m/%Y")

    msg = (
        f"🚨 CardioCare — CẢNH BÁO KHẨN CẤP\n"
        f"Bệnh nhân: {patient_name}\n"
        f"Triệu chứng: {syms}\n"
        f"Thời gian: {thoi_gian}\n"
        f"Vui lòng liên hệ bệnh nhân ngay. Gọi 115 nếu cần."
    )

    # 1. Zalo ZNS
    if zalo.is_configured() and family_phone:
        res = zalo.send_zns(family_phone, {
            "ten_benh_nhan": patient_name, "trieu_chung": syms, "thoi_gian": thoi_gian,
        }, tracking_id=f"red-{patient_id}")
        print(f"[alert] Zalo người thân ({family_phone}): {'OK' if res.get('ok') else 'lỗi'}")
        return

    # 2. Telegram (kênh chính hiện tại)
    if telegram.is_configured():
        res = telegram.send_message(msg)
        print(f"[alert] Telegram người thân: {'OK' if res.get('ok') else 'lỗi'}")
        return

    # 3. SMS Twilio
    if family_phone:
        from services import telephony
        sms_body = (
            f"[CardioCare] KHAN CAP: Benh nhan {patient_name} co dau hieu {syms} "
            f"luc {thoi_gian}. Vui long lien he ngay. Goi 115 neu can."
        )
        res = telephony.send_sms(family_phone, sms_body)
        tag = "mô phỏng" if res.get("simulated") else ("OK" if res.get("ok") else "lỗi")
        print(f"[alert] SMS người thân ({family_phone}): {tag}")
        return

    # 4. Mô phỏng
    print(f"[alert] (mô phỏng) báo người thân BN {patient_id}: {syms}")


def _send_email(subject: str, body: str) -> bool:
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"]    = settings.ALERT_EMAIL_FROM
        msg["To"]      = settings.ALERT_EMAIL_TO
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=8) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[alert] Email thất bại: {e}")
        return False
