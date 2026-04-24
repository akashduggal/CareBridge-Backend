import uuid
from sqlalchemy import Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base

class CallAttempt(Base):
    __tablename__ = "call_attempt"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discharge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_secs: Mapped[int] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=True)  # completed|voicemail|no_answer|refused|wrong_party
    transcript: Mapped[str] = mapped_column(Text, nullable=True)
    twilio_call_sid: Mapped[str] = mapped_column(Text, unique=True, nullable=True)