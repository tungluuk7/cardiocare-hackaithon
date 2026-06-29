import asyncio
import sys

# Tránh UnicodeEncodeError khi in tiếng Việt trên Windows (console mặc định cp1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.triage_engine import analyze

# (transcript, level kỳ vọng)
cases = [
    ("bác cảm thấy bình thường, ăn uống tốt",        "GREEN"),
    ("hơi khó thở, chân cũng hơi sưng",               "YELLOW"),
    ("đau ngực dữ dội từ sáng, ngất một lần",         "RED"),
    # Phủ định / đối kháng — các case từng sai với logic cửa sổ ký tự cũ
    ("không đau ngực",                                "GREEN"),
    ("con không lo, bác bị ngất sáng nay",            "RED"),
    ("không bị sốt, giờ lại sốt cao",                 "YELLOW"),
    ("không thấy mệt nhưng bị đau ngực dữ dội",       "RED"),
]

passed = 0
for transcript, expected in cases:
    r = asyncio.run(analyze(transcript))
    ok = r.level == expected
    passed += ok
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {r.level:6} (kỳ vọng {expected:6}) | {r.symptoms} | '{transcript[:45]}'")

print()
print(f"Kết quả: {passed}/{len(cases)} pass")
sys.exit(0 if passed == len(cases) else 1)
