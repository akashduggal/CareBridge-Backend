from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

# --- REQUEST ---
class DischargeCreate(BaseModel):
    patient_id: UUID
    discharged_at: datetime
    admitting_dx: str
    discharge_dx_group: str | None = None   # CHF|COPD|AMI|PNEUMONIA|ORTHO|OTHER
    medications: dict | None = None
    baseline_risk: str = "medium"           # low|medium|high
    attending_md: str | None = None

# --- RESPONSE ---
class DischargeOut(BaseModel):
    id: UUID
    patient_id: UUID
    discharged_at: datetime
    admitting_dx: str
    discharge_dx_group: str | None
    medications: dict | None
    baseline_risk: str
    first_call_at: datetime | None         # auto-calculated: discharged_at + 36h
    call_status: str
    attending_md: str | None
    created_at: datetime

    model_config = {"from_attributes": True}