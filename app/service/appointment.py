from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Status,
    appointment as Appointment,
    Doctors,
    Patient,
    Slots,
)
from app.schemas import AppointmentCreate, CancelAppointmentRequest


def check_doctor_availability(
    doctor_id: int,
    db: Session,
    requested_date: date,
):
    doctor = (
        db.query(Doctors)
        .filter(Doctors.id == doctor_id, Doctors.is_active.is_(True))
        .first()
    )
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active doctor not found",
        )

    start_of_day = datetime.combine(requested_date, time.min)
    start_of_next_day = start_of_day + timedelta(days=1)

    booked_slot_ids = (
        db.query(Appointment.slot_id)
        .filter(Appointment.status != Status.CANCELLED)
        .subquery()
    )

    return (
        db.query(Slots)
        .filter(
            Slots.doctor_id == doctor_id,
            Slots.start_time >= start_of_day,
            Slots.start_time < start_of_next_day,
            ~Slots.id.in_(booked_slot_ids),
        )
        .order_by(Slots.start_time)
        .all()
    )


def check_slot_availability(slot_id: int, db: Session):
    slot = db.query(Slots).filter(Slots.id == slot_id).first()
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.slot_id == slot_id,
            Appointment.status != Status.CANCELLED,
        )
        .first()
    )
    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot is already booked",
        )

    return slot


def book_appointment(appointment_data: AppointmentCreate, db: Session):
    doctor = (
        db.query(Doctors)
        .filter(
            Doctors.id == appointment_data.doctor_id,
            Doctors.is_active.is_(True),
        )
        .first()
    )
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active doctor not found",
        )

    slot = check_slot_availability(appointment_data.slot_id, db)
    if slot.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected slot does not belong to this doctor",
        )
    if slot.start_time <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book a slot in the past",
        )

    phone_number = appointment_data.phone_number.strip()
    patient = db.query(Patient).filter(Patient.phone == phone_number).first()
    if patient is None:
        patient = Patient(
            name=appointment_data.patient_name.strip(),
            phone=phone_number,
        )
        db.add(patient)
        db.flush()

    new_appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        status=Status.CONFIRMED,
    )

    try:
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)
    except Exception:
        db.rollback()
        raise

    return new_appointment


def cancel_appointment(
    appointment_id: int,
    cancellation_data: CancelAppointmentRequest,
    db: Session,
):
    existing_appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if not existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    patient = (
        db.query(Patient)
        .filter(Patient.id == existing_appointment.patient_id)
        .first()
    )
    if patient is None or patient.phone != cancellation_data.phone_number.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone number does not match the appointment patient",
        )

    if existing_appointment.status == Status.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment is already cancelled",
        )

    existing_appointment.status = Status.CANCELLED
    try:
        db.commit()
        db.refresh(existing_appointment)
    except Exception:
        db.rollback()
        raise

    return existing_appointment
