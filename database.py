import sqlite3
from config import settings

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            phone         TEXT NOT NULL,
            age           INTEGER,
            doctor_name   TEXT,
            discharge_date TEXT,
            diagnosis     TEXT,
            created_at    TEXT DEFAULT (datetime('now','+7 hours'))
        );

        CREATE TABLE IF NOT EXISTS call_logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id    INTEGER NOT NULL REFERENCES patients(id),
            called_at     TEXT DEFAULT (datetime('now','+7 hours')),
            transcript    TEXT,
            audio_path    TEXT,
            status        TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS triage_results (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            call_log_id    INTEGER NOT NULL REFERENCES call_logs(id),
            level          TEXT NOT NULL,   -- GREEN / YELLOW / RED
            symptoms       TEXT,            -- JSON list of symptom IDs
            symptom_labels TEXT,            -- JSON list of human-readable labels
            confidence     REAL,
            alert_sent     INTEGER DEFAULT 0,
            created_at     TEXT DEFAULT (datetime('now','+7 hours'))
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id   INTEGER,
            patient_name TEXT,
            level        TEXT,
            symptoms     TEXT,            -- JSON list of symptom labels
            message      TEXT,
            created_at   TEXT DEFAULT (datetime('now','+7 hours')),
            seen         INTEGER DEFAULT 0
        );
        """)

        # Migration: thêm column thiếu cho DB cũ (CREATE TABLE IF NOT EXISTS
        # không alter table đã tồn tại). An toàn khi chạy nhiều lần.
        for table, column, ddl in [
            ("triage_results", "symptom_labels", "ALTER TABLE triage_results ADD COLUMN symptom_labels TEXT"),
            ("patients", "call_time", "ALTER TABLE patients ADD COLUMN call_time TEXT"),            # giờ hẹn gọi "HH:MM"
            ("patients", "last_call_date", "ALTER TABLE patients ADD COLUMN last_call_date TEXT"),   # ngày đã GỌI ĐI (tránh gọi trùng trong ngày)
            ("patients", "last_answered_at", "ALTER TABLE patients ADD COLUMN last_answered_at TEXT"), # thời điểm bệnh nhân NHẤC MÁY gần nhất
            ("patients", "family_phone", "ALTER TABLE patients ADD COLUMN family_phone TEXT"),         # SĐT người thân (gửi Zalo khi RED)
        ]:
            existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if column not in existing:
                conn.execute(ddl)
