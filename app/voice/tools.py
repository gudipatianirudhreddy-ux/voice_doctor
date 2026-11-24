"""Groq/Pipecat function-call adapters for the appointment service."""
from datetime import date
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_

from app.database import SessionLocal
from app.models import Doctors, Patient, Slots, appointment as Appointment
from app.schemas import AppointmentCreate, CancelAppointmentRequest
from app.service.appointment import (
    book_appointment as create_appointment,
    cancel_appointment as cancel_existing_appointment,
    check_doctor_availability as get_available_slots,
)


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _appointment_payload(db, appointment: Appointment) -> dict[str, Any]:
    doctor = db.query(Doctors).filter(Doctors.id == appointment.doctor_id).first()
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    slot = db.query(Slots).filter(Slots.id == appointment.slot_id).first()
    return {
        "success": True,
        "appointment_id": appointment.id,
        "status": appointment.status.value,
        "doctor_name": doctor.name if doctor else None,
        "specialty": doctor.specialty if doctor else None,
        "patient_name": patient.name if patient else None,
        "slot_id": appointment.slot_id,
        "start_time": _iso(slot.start_time) if slot else None,
        "end_time": _iso(slot.end_time) if slot else None,
    }


async def _send(params, payload: dict[str, Any]) -> None:
    await params.result_callback(payload)


async def find_doctors(params, search_term: str):
    """Search active doctors by name or specialty.

    Args:
        search_term: Doctor name or specialty, for example cardiology.
    """
    term = search_term.strip()
    if not term:
        await _send(params, {"success": False, "message": "Ask for a doctor name or specialty."})
        return

    db = SessionLocal()
    try:
        doctors = (
            db.query(Doctors)
            .filter(
                Doctors.is_active.is_(True),
                or_(Doctors.name.ilike(f"%{term}%"), Doctors.specialty.ilike(f"%{term}%")),
            )
            .order_by(Doctors.name)
            .limit(10)
            .all()
        )
        await _send(params, {
            "success": True,
            "doctors": [
                {"doctor_id": d.id, "name": d.name, "specialty": d.specialty, "description": d.description}
                for d in doctors
            ],
            "message": "No active doctors matched." if not doctors else None,
        })
    except Exception:
        await _send(params, {"success": False, "message": "Doctor search failed temporarily."})
    finally:
        db.close()


async def check_doctor_availability(params, doctor_id: int, requested_date: str):
    """Check available slots for a doctor on a date.

    Args:
        doctor_id: Doctor ID returned by find_doctors.
        requested_date: Date as YYYY-MM-DD.
    """
    try:
        day = date.fromisoformat(requested_date)
        doctor_id = int(doctor_id)
    except (KeyError, TypeError, ValueError):
        await _send(params, {"success": False, "message": "Provide a valid doctor ID and YYYY-MM-DD date."})
        return

    db = SessionLocal()
    try:
        doctor = db.query(Doctors).filter(Doctors.id == doctor_id, Doctors.is_active.is_(True)).first()
        if doctor is None:
            await _send(params, {"success": False, "message": "Active doctor not found."})
            return
        slots = get_available_slots(doctor_id, db, day)
        await _send(params, {
            "success": True,
            "doctor_id": doctor.id,
            "doctor_name": doctor.name,
            "specialty": doctor.specialty,
            "requested_date": day.isoformat(),
            "available_slots": [
                {"slot_id": s.id, "start_time": _iso(s.start_time), "end_time": _iso(s.end_time)}
                for s in slots
            ],
            "message": "No available slots for that date." if not slots else None,
        })
    except HTTPException as exc:
        await _send(params, {"success": False, "message": exc.detail})
    except Exception:
        await _send(params, {"success": False, "message": "Availability check failed temporarily."})
    finally:
        db.close()


async def book_appointment(params, doctor_id: int, slot_id: int, patient_name: str, phone_number: str):
    """Book a slot only after the caller confirms doctor, date, time, name and phone.

    Args:
        doctor_id: Doctor ID returned by find_doctors.
        slot_id: Slot ID returned by check_doctor_availability.
        patient_name: Caller full name.
        phone_number: Caller phone number, repeated back and confirmed.
    """
    db = SessionLocal()
    try:
        payload = AppointmentCreate(
            doctor_id=int(doctor_id),
            slot_id=int(slot_id),
            patient_name=patient_name.strip(),
            phone_number=phone_number.strip(),
        )
        appointment = create_appointment(payload, db)
        await _send(params, _appointment_payload(db, appointment))
    except HTTPException as exc:
        await _send(params, {"success": False, "message": exc.detail})
    except (KeyError, TypeError, ValueError):
        await _send(params, {"success": False, "message": "Booking details were invalid. Confirm them with the caller."})
    except Exception:
        await _send(params, {"success": False, "message": "Booking failed temporarily. Do not claim it was booked."})
    finally:
        db.close()


async def cancel_appointment(params, appointment_id: int, phone_number: str):
    """Cancel after collecting appointment ID and verifying the registered phone.

    Args:
        appointment_id: Appointment ID provided or confirmed by the caller.
        phone_number: Phone number registered for the appointment.
    """
    db = SessionLocal()
    try:
        appointment_id = int(appointment_id)
        request = CancelAppointmentRequest(phone_number=phone_number.strip())
        appointment = cancel_existing_appointment(appointment_id, request, db)
        await _send(params, _appointment_payload(db, appointment))
    except HTTPException as exc:
        await _send(params, {"success": False, "message": exc.detail})
    except (KeyError, TypeError, ValueError):
        await _send(params, {"success": False, "message": "Appointment ID or phone number is invalid."})
    except Exception:
        await _send(params, {"success": False, "message": "Cancellation failed temporarily. Do not claim it was cancelled."})
    finally:
        db.close()
