
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import Doctors, Slots


def seed_data():
    db = SessionLocal()

    try:
        # Avoid inserting duplicate doctors every time
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

        slots = []

        for doctor in doctors:
            for hour in [9, 10, 11, 14, 15]:
                start_time = datetime.now().replace(
                    hour=hour,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

                slots.append(
                    Slots(
                        doctor_id=doctor.id,
                        date=start_time,
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
