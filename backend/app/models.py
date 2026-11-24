import enum
from .database import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from sqlalchemy import Boolean
from sqlalchemy import ForeignKey

class Status(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
class Doctors(Base):
    __tablename__="doctors"

    id=Column(BigInteger, primary_key=True, index=True)
    name=Column(String,index=True)
    specialty=Column(String,index=True)
    description=Column(String,nullable=False)
    is_active=Column(Boolean,default=False)

class Slots(Base):
    __tablename__="slots"
    id=Column(BigInteger, primary_key=True, index=True)
    doctor_id=Column(BigInteger, ForeignKey("doctors.id"))
    start_time=Column(DateTime, nullable=False)
    end_time=Column(DateTime, nullable=False)

class Patient(Base):
    __tablename__="patients"
    id=Column(BigInteger, primary_key=True,index=True)
    name=Column(String, nullable=False)
    phone=Column(String(20), nullable=False, unique=True)
    created_at=Column(DateTime(timezone=True),server_default=func.now())

class appointment(Base):
    __tablename__="appointments"
    id=Column(BigInteger, primary_key=True,index=True)
    patient_id=Column(BigInteger, ForeignKey("patients.id"))
    doctor_id=Column(BigInteger, ForeignKey("doctors.id"))
    slot_id=Column(BigInteger, ForeignKey("slots.id"))
    status=Column(SQLAlchemyEnum(Status,name="status"), default=Status.PENDING)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    