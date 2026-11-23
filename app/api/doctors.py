
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import Doctors
from app.database import get_db
from app.service.appointment import check_doctor_availability

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)


@router.get("/")
def get_doctors(db: Session = Depends(get_db)):
    doctors = db.query(Doctors).all()
    return doctors


@router.get("/{doctor_id}/availability")
def get_doctor_availability(
    doctor_id: int,
    requested_date: datetime,
    db: Session = Depends(get_db),
):
    slots = check_doctor_availability(
        doctor_id=doctor_id,
        db=db,
        requested_date=requested_date,
    )

    return {
        "doctor_id": doctor_id,
        "requested_date": requested_date,
        "available_slots": slots,
    }
