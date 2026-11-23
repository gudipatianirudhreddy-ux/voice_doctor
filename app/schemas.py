from pydantic import BaseModel, ConfigDict
from datetime import datetime


class DoctorCreate(BaseModel):
    name: str
    specialty: str
    description: str | None = None


class DoctorResponse(BaseModel):
    id: int
    name: str
    specialty: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)

class AppointmentCreate(BaseModel):
    doctor_id: int
    slot_id: int
    patient_name: str
    phone_number: str


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    slot_id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)