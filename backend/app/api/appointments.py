from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctors, Patient, Slots, appointment as Appointment
from app.schemas import AppointmentCreate, CancelAppointmentRequest, RescheduleAppointmentRequest
from app.service.appointment import book_appointment, cancel_appointment, reschedule_appointment

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/")
def list_appointments(
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return recent appointments for the demo dashboard.

    Patient phone numbers are intentionally not included in this read response.
    """
    rows = (
        db.query(
            Appointment,
            Patient.name,
            Doctors.name,
            Doctors.specialty,
            Slots.start_time,
            Slots.end_time,
        )
        .join(Patient, Patient.id == Appointment.patient_id)
        .join(Doctors, Doctors.id == Appointment.doctor_id)
        .join(Slots, Slots.id == Appointment.slot_id)
        .order_by(Appointment.created_at.desc(), Appointment.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "appointment_id": appointment.id,
            "patient_name": patient_name,
            "doctor_id": appointment.doctor_id,
            "doctor_name": doctor_name,
            "specialty": specialty,
            "slot_id": appointment.slot_id,
            "start_time": start_time,
            "end_time": end_time,
            "status": appointment.status.value,
            "created_at": appointment.created_at,
        }
        for (
            appointment,
            patient_name,
            doctor_name,
            specialty,
            start_time,
            end_time,
        ) in rows
    ]


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
