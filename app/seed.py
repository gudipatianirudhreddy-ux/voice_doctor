from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import Doctors, Slots


def seed_data():
    db = SessionLocal()
    try:
        if db.query(Doctors).count() > 0:
            print("Doctors already exist. Skipping seed.")
            return

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

        # Seed appointments for tomorrow so the sample slots are in the future.
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        slots = []
        for doctor in doctors:
            for hour in [9, 10, 11, 14, 15]:
                start_time = datetime.combine(
                    tomorrow,
                    datetime.min.time(),
                ).replace(hour=hour)
                slots.append(
                    Slots(
                        doctor_id=doctor.id,
                        start_time=start_time,
                        end_time=start_time + timedelta(minutes=30),
                    )
                )

        db.add_all(slots)
        db.commit()
        print("Sample doctors and slots added successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
