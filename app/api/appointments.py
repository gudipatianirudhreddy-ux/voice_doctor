
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import AppointmentCreate
from app.service.appointment import book_appointment, cancel_appointment


router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"],
)


@router.post("/")
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
):
    return book_appointment(
        appointment_data=appointment_data,
        db=db,
    )


@router.post("/{appointment_id}/cancel")
def cancel_existing_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
):
    return cancel_appointment(
        appointment_id=appointment_id,
        db=db,
    )
