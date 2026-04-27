from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from carebridge.app.database import AsyncSessionLocal
from carebridge.app.models.discharge import DischargeEvent
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# This is the job that runs every 60 seconds
async def check_pending_calls():
    logger.info("⏰ Scheduler: checking for pending calls...")

    async with AsyncSessionLocal() as db:
        try:
            # Find discharges that are:
            # 1. status = pending
            # 2. first_call_at is in the past (it's time to call)
            # SELECT FOR UPDATE SKIP LOCKED = prevents two workers
            # from grabbing the same row at the same time
            result = await db.execute(
                text("""
                    SELECT id, patient_id, admitting_dx, baseline_risk
                    FROM discharge_event
                    WHERE call_status = 'pending'
                    AND first_call_at < NOW()
                    FOR UPDATE SKIP LOCKED
                """)
            )
            rows = result.fetchall()

            if not rows:
                logger.info("✅ No pending calls due right now.")
                return

            for row in rows:
                discharge_id = row.id
                patient_id = row.patient_id

                # Mark as in_progress so another scheduler tick
                # doesn't pick up the same discharge
                await db.execute(
                    text("""
                        UPDATE discharge_event
                        SET call_status = 'in_progress'
                        WHERE id = :id
                    """),
                    {"id": discharge_id}
                )

                # Day 3: this is where Twilio call gets triggered
                # For now just log it
                logger.info(
                    f"📞 Would call patient {patient_id} "
                    f"for discharge {discharge_id} "
                    f"(dx: {row.admitting_dx}, risk: {row.baseline_risk})"
                )

            await db.commit()
            logger.info(f"✅ Processed {len(rows)} pending discharge(s).")

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Scheduler error: {e}")


# Create the scheduler instance
scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(
        check_pending_calls,
        trigger="interval",
        seconds=60,
        id="check_pending_calls",
        replace_existing=True
    )
    scheduler.start()
    logger.info("🚀 Scheduler started — checking every 60 seconds.")