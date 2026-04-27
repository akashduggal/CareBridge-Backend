from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID

# --- REQUEST schema (what the client sends us) ---
class PatientCreate(BaseModel):
    name: str
    dob: date
    phone: str          # E.164 format e.g. +16025550142
    mrn: str | None = None
    tcpa_consent: bool = True

# --- RESPONSE schema (what we send back) ---
class PatientOut(BaseModel):
    id: UUID
    name: str
    dob: date
    phone: str
    mrn: str | None
    tcpa_consent: bool
    created_at: datetime

    # This tells Pydantic to read from SQLAlchemy objects, not just dicts
    model_config = {"from_attributes": True}