
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import (
    appointment as Appointment,
    Doctors,
    Slots,
    Patient,
)
from app.schemas import AppointmentCreate, AppointmentResponse


def check_doctor_availability(
    doctor_id: int,
    db: Session,
    requested_date: datetime,
):
    doctor = (
        db.query(Doctors)
        .filter(Doctors.id == doctor_id)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    slots = (
        db.query(Slots)
        .filter(
            Slots.doctor_id == doctor_id,
            Slots.date == requested_date,
        )
        .all()
    )

    return slots


def check_slot_availability(
    slot_id: int,
    db: Session,
):
    slot = (
        db.query(Slots)
        .filter(Slots.id == slot_id)
        .first()
    )

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    # Check whether this slot already has an appointment.
    existing_appointment = (
        db.query(Appointment)
        .filter(Appointment.slot_id == slot_id)
        .first()
    )

    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot is already booked",
        )

    return slot


def book_appointment(
    appointment_data: AppointmentCreate,
    db: Session,
):
    # Verify doctor exists.
    doctor = (
        db.query(Doctors)
        .filter(Doctors.id == appointment_data.doctor_id)
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # Verify slot exists and is available.
    slot = check_slot_availability(
        appointment_data.slot_id,
        db,
    )

    # Ensure the selected slot belongs to the selected doctor.
    if slot.doctor_id != appointment_data.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected slot does not belong to this doctor",
        )

    # Ensure the selected slot matches the requested date.
    if slot.date.date() != appointment_data.appointment_date.date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected slot does not match the requested date",
        )

    # Create appointment.
    new_appointment = Appointment(
        doctor_id=appointment_data.doctor_id,
        slot_id=appointment_data.slot_id,
        # Add patient_id here once your schema/service
        # resolves the patient using their phone number.
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

    # Update this according to your actual Status enum.
    existing_appointment.status = "cancelled"

    db.commit()
    db.refresh(existing_appointment)

    return existing_appointment
