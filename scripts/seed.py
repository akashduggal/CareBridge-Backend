import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta, date
import uuid
import ssl

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from carebridge.app.models.patient import Patient
from carebridge.app.models.discharge import DischargeEvent

DATABASE_URL = os.getenv("DATABASE_URL").split("?")[0]

ssl_context = ssl.create_default_context()
engine = create_async_engine(DATABASE_URL, connect_args={"ssl": ssl_context})
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

patients = [
    {"name": "James Okafor",   "dob": date(1948, 3, 12), "phone": "+16025550101", "mrn": "MRN001"},
    {"name": "Linda Matsuda",  "dob": date(1955, 7, 28), "phone": "+16025550102", "mrn": "MRN002"},
    {"name": "Robert Chen",    "dob": date(1942, 11, 5), "phone": "+16025550103", "mrn": "MRN003"},
    {"name": "Maria Gonzalez", "dob": date(1960, 1, 19), "phone": "+16025550104", "mrn": "MRN004"},
    {"name": "David Williams", "dob": date(1938, 9, 3),  "phone": "+16025550105", "mrn": "MRN005"},
]

discharges = [
    {"dx_group": "CHF",       "admitting_dx": "Heart Failure with reduced EF",        "risk": "high",   "days_ago": 1},
    {"dx_group": "COPD",      "admitting_dx": "COPD exacerbation",                    "risk": "medium", "days_ago": 2},
    {"dx_group": "AMI",       "admitting_dx": "Acute Myocardial Infarction (NSTEMI)", "risk": "high",   "days_ago": 3},
    {"dx_group": "PNEUMONIA", "admitting_dx": "Community-acquired pneumonia",          "risk": "medium", "days_ago": 4},
    {"dx_group": "ORTHO",     "admitting_dx": "Right hip replacement",                "risk": "low",    "days_ago": 5},
]

async def seed():
    async with AsyncSessionLocal() as db:
        # Insert patients
        patient_ids = []
        for p in patients:
            patient = Patient(
                id=uuid.uuid4(),
                name=p["name"],
                dob=p["dob"],
                phone=p["phone"],
                mrn=p["mrn"],
                tcpa_consent=True
            )
            db.add(patient)
            patient_ids.append(patient.id)

        await db.flush()  # assigns IDs before we use them below

        # Insert discharge events
        now = datetime.utcnow()
        for i, d in enumerate(discharges):
            discharged_at = now - timedelta(days=d["days_ago"])
            first_call_at = discharged_at + timedelta(hours=36)
            # If first_call_at is in the past, mark as pending so scheduler picks it up
            status = "pending"

            discharge = DischargeEvent(
                id=uuid.uuid4(),
                patient_id=patient_ids[i],
                discharged_at=discharged_at,
                admitting_dx=d["admitting_dx"],
                discharge_dx_group=d["dx_group"],
                baseline_risk=d["risk"],
                first_call_at=first_call_at,
                call_status=status,
                attending_md="Dr. Sarah Patel"
            )
            db.add(discharge)

        await db.commit()
        print("✅ Seeded 5 patients and 5 discharge events")

if __name__ == "__main__":
    asyncio.run(seed())