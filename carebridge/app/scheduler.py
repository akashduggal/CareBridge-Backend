
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from carebridge.app.models.call import CallAttempt
from carebridge.app.models.patient import Patient
from sqlalchemy import select
from carebridge.app.config.database import AsyncSessionLocal
from carebridge.app.models.discharge import DischargeEvent
from datetime import datetime, timezone
import logging
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))



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


            now = datetime.now(timezone.utc)
            results = await db.execute(
                select(DischargeEvent)
                .where(
                    DischargeEvent.call_status == "pending",
                    DischargeEvent.call_at.is_not(None),
                    DischargeEvent.call_at <= now,
                    DischargeEvent.call_attempt_count < DischargeEvent.max_call_attempts,
                )
                .with_for_update(skip_locked=True)
            )
            discharges = results.scalars().all()
            if not discharges:
                logger.info("✅ No pending calls due right now.")
                return
            patient_ids = [d.patient_id for d in discharges]

            patient_results = await db.execute(
                select(Patient).where(Patient.id.in_(patient_ids))
            )

            patients_by_id = {
                p.id: p for p in patient_results.scalars().all()
            }


            for discharge in discharges:
                discharge_id = discharge.id
                patient_id = discharge.patient_id
                patient = patients_by_id.get(discharge.patient_id)

                if not patient:
                    discharge.call_status = "failed"
                    logger.error(f"Patient not found for id: {patient_id}")
                    continue
                if not patient.tcpa_consent:
                    logger.warning(f"Patient {patient_id} has not given TCPA consent. Marking call as refused.")
                    discharge.call_status = "refused"
                    continue

                discharge.call_attempt_count += 1

                call = client.calls.create(
                    to=patient.phone,
                    from_=os.getenv("TWILIO_PHONE_NUMBER"),
                    url=f"{os.getenv('WEBHOOK_BASE_URL')}/voice/outbound?discharge_id={discharge_id}",
                    status_callback=f"{os.getenv('WEBHOOK_BASE_URL')}/voice/status",
                    status_callback_event=[
                        "completed",
                        "failed",
                        "busy",
                        "no-answer",
                        "canceled",
                    ],
                    status_callback_method="POST"
                )     
                call_attempt = CallAttempt(
                    discharge_id=discharge_id,
                    attempt_number=discharge.call_attempt_count,
                    twilio_call_sid=call.sid,
                    status="initiated",
                )

                db.add(call_attempt)

                discharge.call_status = "in_progress"

                # Day 3: this is where Twilio call gets triggered
                # For now just log it
                
                

                logger.info(
                    f"📞 Called patient {patient_id} "
                    f"for discharge {discharge_id} "
                    f"attempt: {discharge.call_attempt_count}, Call_sid: {call.sid}"
                )

            await db.commit()
            logger.info(f"✅ Processed {len(discharges)} pending discharge(s).")

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