import uuid
from sqlalchemy import Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Text, Integer, DateTime, ForeignKey
from datetime import datetime, timezone
from .base import Base

class CallAttempt(Base):
    __tablename__ = "call_attempt"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discharge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("discharge_event.id", ondelete="CASCADE"),nullable=False,index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=True)
    duration_secs: Mapped[int] = mapped_column(Integer, nullable=True)
    twilio_call_sid: Mapped[str] = mapped_column(Text,unique=True,nullable=True,index=True)
    status: Mapped[str] = mapped_column(Text,default="initiated")# initiated | ringing | in_progress | completed | failed | no_answer | busy | canceled
    outcome: Mapped[str] = mapped_column(Text,nullable=True)# completed | voicemail | no_answer | refused | wrong_party
    transcript: Mapped[str] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)