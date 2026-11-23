from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import Doctors, Slots


SAMPLE_HOURS = [9, 10, 11, 14, 15]


def seed_data():
    db = SessionLocal()
    try:
        # Reuse existing doctors. Add sample doctors only when the table is empty.
        doctors = db.query(Doctors).filter(Doctors.is_active.is_(True)).all()
        if not doctors:
            doctors = [
                Doctors(
                    name="Dr. Sharma",
                    specialty="Cardiology",
                    description="Experienced cardiologist",
                    is_active=True,
                ),
                Doctors(
                    name="Dr. Reddy",
                    specialty="Dermatology",
                    description="Skin and hair specialist",
                    is_active=True,
                ),
                Doctors(
                    name="Dr. Mehta",
                    specialty="General Physician",
                    description="General health consultations",
                    is_active=True,
                ),
            ]
            db.add_all(doctors)
            db.flush()

        # Use tomorrow's date, and only insert missing doctor/time combinations.
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        day_start = datetime.combine(tomorrow, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        added_count = 0

        for doctor in doctors:
            existing_times = {
                slot.start_time
                for slot in (
                    db.query(Slots)
                    .filter(
                        Slots.doctor_id == doctor.id,
                        Slots.start_time >= day_start,
                        Slots.start_time < day_end,
                    )
                    .all()
                )
            }

            for hour in SAMPLE_HOURS:
                start_time = day_start.replace(hour=hour)
                if start_time in existing_times:
                    continue

                db.add(
                    Slots(
                        doctor_id=doctor.id,
                        start_time=start_time,
                        end_time=start_time + timedelta(minutes=30),
                    )
                )
                added_count += 1

        db.commit()
        print(f"Seed completed. Added {added_count} missing slots for {tomorrow}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
