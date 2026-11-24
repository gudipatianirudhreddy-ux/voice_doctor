from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    patient_name: str = Field(min_length=1, max_length=120)
    phone_number: str = Field(min_length=7, max_length=20)


class CancelAppointmentRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=20)


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    slot_id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RescheduleAppointmentRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=20)
    new_slot_id: int
