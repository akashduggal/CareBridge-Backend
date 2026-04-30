import uuid
from sqlalchemy import Text, Integer, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timezone
from sqlalchemy import Text, Integer, Boolean, DateTime, ForeignKey
from .base import Base

class CallOutcome(Base):
    __tablename__ = "call_outcome"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("call_attempt.id", ondelete="CASCADE"),nullable=False,index=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)  # 1|2|3
    auto_escalate: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_escalate_reason: Mapped[str] = mapped_column(Text, nullable=True)
    flags: Mapped[dict] = mapped_column(JSONB, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc))
    score_reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    medication_adherent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    symptoms_worsening: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_followup_appointment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_home_support: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    emergency_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class EscalationAction(Base):
    __tablename__ = "escalation_action"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_outcome_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)  # sms_patient|nurse_queue|on_call_sms|911_advisory
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_ref: Mapped[str] = mapped_column(Text, nullable=True)