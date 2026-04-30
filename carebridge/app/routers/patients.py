from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from carebridge.app.config.database import get_db
from carebridge.app.models.patient import Patient
from carebridge.app.schemas.patient import PatientCreate, PatientOut

router = APIRouter(prefix="/patients", tags=["patients"])

# POST /patients
@router.post("/", response_model=PatientOut, status_code=201)
async def create_patient(payload: PatientCreate, db: AsyncSession = Depends(get_db)):
    patient = Patient(**payload.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient

# GET /patients
@router.get("/", response_model=list[PatientOut])
async def list_patients(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Patient).offset(offset).limit(limit)
    )
    return result.scalars().all()