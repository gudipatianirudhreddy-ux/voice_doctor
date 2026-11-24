from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AppointmentCreate, CancelAppointmentRequest, RescheduleAppointmentRequest
from app.service.appointment import book_appointment, cancel_appointment, reschedule_appointment

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
):
    return book_appointment(appointment_data=appointment_data, db=db)


@router.post("/{appointment_id}/cancel")
def cancel_existing_appointment(
    appointment_id: int,
    cancellation_data: CancelAppointmentRequest,
    db: Session = Depends(get_db),
):
    return cancel_appointment(
        appointment_id=appointment_id,
        cancellation_data=cancellation_data,
        db=db,
    )


@router.put("/{appointment_id}/reschedule")
def reschedule_existing_appointment(
    appointment_id: int,
    request: RescheduleAppointmentRequest,
    db: Session = Depends(get_db),
):
    return reschedule_appointment(
        appointment_id=appointment_id,
        phone_number=request.phone_number,
        new_slot_id=request.new_slot_id,
        db=db,
    )
