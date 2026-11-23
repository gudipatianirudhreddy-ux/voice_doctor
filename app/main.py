
from fastapi import FastAPI

from app.api import doctors, appointments

app = FastAPI(
    title="NexovAI Voice Doctor",
    description="Voice-based doctor appointment assistant",
    version="1.0.0",
)

app.include_router(doctors.router)
app.include_router(appointments.router)


@app.get("/")
def root():
    return {
        "message": "NexovAI Voice Doctor API is running"
    }

