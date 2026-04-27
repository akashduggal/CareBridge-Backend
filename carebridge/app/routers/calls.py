from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from carebridge.app.database import get_db
from carebridge.app.models.call import CallAttempt

router = APIRouter(prefix="/calls", tags=["calls"])

# GET /calls
@router.get("/")
async def list_calls(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CallAttempt).offset(offset).limit(limit)
    )
    return result.scalars().all()

# GET /calls/{id}/transcript
@router.get("/{call_id}/transcript")
async def get_transcript(call_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CallAttempt).where(CallAttempt.id == call_id)
    )
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"call_id": call_id, "transcript": call.transcript}