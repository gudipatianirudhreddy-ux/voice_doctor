import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import doctors, appointments

app = FastAPI(
    title="NexovAI Voice Doctor",
    description="Voice-based doctor appointment assistant",
    version="1.0.0",
)

# Keep local development origins configurable for whichever frontend port is used.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(doctors.router)
app.include_router(appointments.router)


@app.get("/")
def root():
    return {
        "message": "NexovAI Voice Doctor API is running"
    }
