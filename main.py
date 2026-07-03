import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from api.patients import router as patients_router
from api.calls import router as calls_router
from api.chatbot import router as chatbot_router
from api.telephony import router as telephony_router
from api.ux import router as ux_router

app = FastAPI(title="CardioCare", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # hackathon — relax sau production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients_router)
app.include_router(calls_router)
app.include_router(chatbot_router)
app.include_router(telephony_router)
app.include_router(ux_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Lời nhắn thoại gọi lại bệnh nhân (sinh bởi POST /calls/{id}/callback)
os.makedirs("callbacks", exist_ok=True)
app.mount("/callbacks", StaticFiles(directory="callbacks"), name="callbacks")

@app.on_event("startup")
async def startup():
    create_tables()
    from services import scheduler
    scheduler.start()   # bật bộ lập lịch tự động gọi (real/simulation)
    print("✅ CardioCare started — http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")


@app.get("/health")
def health():
    return {"status": "ok"}
