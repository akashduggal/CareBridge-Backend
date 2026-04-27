from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from uuid import UUID
from carebridge.app.database import get_db
from carebridge.app.models.discharge import DischargeEvent
from carebridge.app.schemas.discharge import DischargeCreate, DischargeOut

router = APIRouter(prefix="/discharges", tags=["discharges"])

# POST /discharges
@router.post("/", response_model=DischargeOut, status_code=201)
async def create_discharge(payload: DischargeCreate, db: AsyncSession = Depends(get_db)):
    data = payload.model_dump()
    data["first_call_at"] = data["discharged_at"] + timedelta(hours=36)
    discharge = DischargeEvent(**data)
    db.add(discharge)
    await db.commit()
    await db.refresh(discharge)
    return discharge

# GET /discharges
@router.get("/", response_model=list[DischargeOut])
async def list_discharges(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DischargeEvent).offset(offset).limit(limit)
    )
    return result.scalars().all()

# GET /discharges/{id}
@router.get("/{discharge_id}", response_model=DischargeOut)
async def get_discharge(discharge_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DischargeEvent).where(DischargeEvent.id == discharge_id)
    )
    discharge = result.scalar_one_or_none()
    if not discharge:
        raise HTTPException(status_code=404, detail="Discharge not found")
    return discharge