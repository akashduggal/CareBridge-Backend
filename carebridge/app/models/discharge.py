import uuid
from sqlalchemy import Text, ARRAY, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from .base import Base

class DischargeEvent(Base):
    __tablename__ = "discharge_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    discharged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    admitting_dx: Mapped[str] = mapped_column(Text, nullable=False)
    discharge_dx_group: Mapped[str] = mapped_column(Text, nullable=True)  # CHF|COPD|AMI|PNEUMONIA|ORTHO|OTHER
    medications: Mapped[dict] = mapped_column(JSONB, nullable=True)
    baseline_risk: Mapped[str] = mapped_column(Text, default="medium")  # low|medium|high
    first_call_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    call_status: Mapped[str] = mapped_column(Text, default="pending")  # pending|in_progress|completed|failed|refused
    attending_md: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)