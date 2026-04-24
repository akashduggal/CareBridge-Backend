import uuid
from sqlalchemy import Boolean, Date, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, date
from .base import Base

class Patient(Base):
    __tablename__ = "patient"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)  # E.164 format: +16025550142
    mrn: Mapped[str] = mapped_column(Text, unique=True, nullable=True)
    tcpa_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)