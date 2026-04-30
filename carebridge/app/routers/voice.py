import os
import json
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from sqlalchemy import select
from dotenv import load_dotenv

from carebridge.app.database import AsyncSessionLocal
from carebridge.app.models.discharge import DischargeEvent
from carebridge.app.models.patient import Patient
from carebridge.app.models.call import CallAttempt
from carebridge.app.models.outcome import CallOutcome
from carebridge.app.config.redis import redis_client

from app.services.groq_service import get_opening_message, get_ai_response, score_call
from app.services.escalation import route_escalation

import logging
logger = logging.getLogger(__name__)

load_dotenv()

router = APIRouter(prefix="/voice", tags=["voice"])



@router.post("/outbound")
async def outbound_call(request: Request):
    """
    Twilio calls this when the outbound call connects.
    Returns TwiML with the opening message + first Gather.
    """
    form = await request.form()
    call_sid = form.get("CallSid")
    discharge_id = request.query_params.get("discharge_id")

    if not discharge_id:
        response = VoiceResponse()
        response.say(
            "Sorry, we could not process this call. Please contact your care team. Goodbye.",
            voice="Polly.Joanna"
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                DischargeEvent.id,
                DischargeEvent.patient_id,
                DischargeEvent.baseline_risk,
                Patient.name,
                Patient.phone,
                Patient.dob,
            )
            .join(Patient, Patient.id == DischargeEvent.patient_id)
            .where(DischargeEvent.id == discharge_id)
        )

        row = result.mappings().one_or_none()

    if not row:
        logger.error(f"Discharge not found for id: {discharge_id}")
        response = VoiceResponse()
        response.say(
            "Sorry, we could not process this call. Please contact your care team. Goodbye.",
            voice="Polly.Joanna"
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    # Store session
    state = {
        "discharge_id": str(row["id"]),
        "patient_id": str(row["patient_id"]),
        "patient_name": row["name"],
        "patient_phone": row["phone"],
        "baseline_risk": row["baseline_risk"],
        "history": [],
        "transcript": "",
        "emergency_escalated": False,
        "emergency_detected": False,
    }
    await redis_client.setex(
        f"voice:call:{call_sid}",
        7200,
        json.dumps(state)
    )


    opening = get_opening_message(row["name"])
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"{os.getenv('WEBHOOK_BASE_URL')}/voice/gather?call_sid={call_sid}",
        method="POST",
        speech_timeout=3,
        timeout=10,
        language="en-US"
    )
    gather.say(opening, voice="Polly.Joanna")
    response.append(gather)
    
    # Fallback if patient doesn't speak
    response.redirect(
        f"{os.getenv('WEBHOOK_BASE_URL')}/voice/no-input?call_sid={call_sid}",
        method="POST"
    )

    return Response(content=str(response), media_type="application/xml")


@router.post("/gather")
async def gather_webhook(request: Request):
    """
    Called every time the patient finishes speaking.
    Sends transcript to Groq, returns next TwiML.
    """
    form = await request.form()
    call_sid = request.query_params.get("call_sid") or form.get("CallSid")
    speech_result = form.get("SpeechResult", "")
    
    raw_state = await redis_client.get(f"voice:call:{call_sid}")
    if not raw_state:
        # Session not found, gracefully end
        response = VoiceResponse()
        response.say("Sorry, something went wrong. Goodbye.", voice="Polly.Joanna")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    session = json.loads(raw_state)
    # Append patient speech to history + transcript
    session["history"].append({"role": "user", "content": speech_result})
    session["transcript"] += f"Patient: {speech_result}\n"

    # Check for emergency keywords before sending to Groq
    emergency_keywords = ["chest pain", "chest pressure", "can't breathe", 
                          "cannot breathe", "heart attack", "stroke", "unconscious"]
    is_emergency = any(kw in speech_result.lower() for kw in emergency_keywords)

    if is_emergency:
        agent_reply = (
            "That sounds very serious. Please hang up and call 911 immediately, "
            "or have someone take you to the nearest emergency room right away. "
            "Please do not wait. Goodbye."
        )

        session["emergency_detected"] = True

        session["history"].append({"role": "assistant", "content": agent_reply})
        session["transcript"] += f"Agent: {agent_reply}\n"

        if not session.get("emergency_escalated"):
            route_escalation(
                tier=3,
                patient_name=session["patient_name"],
                patient_phone=session["patient_phone"],
                score=10,
                reasoning="Emergency symptom detected during live call.",
                call_sid=call_sid,
            )
            session["emergency_escalated"] = True

        await redis_client.setex(
            f"voice:call:{call_sid}",
            7200,
            json.dumps(session)
        )

        async with AsyncSessionLocal() as db:
            call_attempt = await db.scalar(
                select(CallAttempt).where(CallAttempt.twilio_call_sid == call_sid)
            )
            if call_attempt:
                call_attempt.transcript = session["transcript"]
                await db.commit()

        response = VoiceResponse()
        response.say(agent_reply, voice="Polly.Joanna")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    else:
        agent_reply = get_ai_response(session["history"], baseline_risk=session["baseline_risk"])

    # Append agent reply to history + transcript
    session["history"].append({"role": "assistant", "content": agent_reply})
    session["transcript"] += f"Agent: {agent_reply}\n"

    await redis_client.setex(
        f"voice:call:{call_sid}",
        7200,
        json.dumps(session)
    )

    async with AsyncSessionLocal() as db:
        call_attempt = await db.scalar(
            select(CallAttempt).where(CallAttempt.twilio_call_sid == call_sid)
        )
        if call_attempt:
            call_attempt.transcript = session["transcript"]
            await db.commit()

    response = VoiceResponse()

    # Check if Groq signaled end of conversation
    if "goodbye" in agent_reply.lower() or is_emergency:
        response.say(agent_reply, voice="Polly.Joanna")
        response.hangup()
    else:
        gather = Gather(
            input="speech",
            action=f"{os.getenv('WEBHOOK_BASE_URL')}/voice/gather?call_sid={call_sid}",
            method="POST",
            speech_timeout=3,
            timeout=10,
            language="en-US"
        )
        gather.say(agent_reply, voice="Polly.Joanna")
        response.append(gather)
        # Fallback if no speech detected
        response.redirect(
            f"{os.getenv('WEBHOOK_BASE_URL')}/voice/no-input?call_sid={call_sid}",
            method="POST"
        )

    return Response(content=str(response), media_type="application/xml")

@router.post("/no-input")
async def no_input_webhook(request: Request):
    call_sid = request.query_params.get("call_sid")
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        call_attempt = await db.scalar(
            select(CallAttempt).where(CallAttempt.twilio_call_sid == call_sid)
        )

        if call_attempt:
            discharge = await db.get(DischargeEvent, call_attempt.discharge_id)

            call_attempt.status = "completed"
            call_attempt.outcome = "no_input"
            call_attempt.ended_at = now

            if discharge:
                if discharge.call_attempt_count >= discharge.max_call_attempts:
                    discharge.call_status = "failed"
                    discharge.call_at = None
                    call_attempt.next_retry_at = None
                else:
                    retry_at = now + timedelta(minutes=30)

                    discharge.call_status = "pending"
                    discharge.call_at = retry_at
                    call_attempt.next_retry_at = retry_at

            await db.commit()

    await redis_client.delete(f"voice:call:{call_sid}")

    response = VoiceResponse()
    response.say(
        "I didn't catch that. We'll try again later. Goodbye.",
        voice="Polly.Joanna"
    )
    response.hangup()

    return Response(content=str(response), media_type="application/xml")

@router.post("/status")
async def call_status(request: Request):
    """
    Called by Twilio when call ends (status=completed).
    Triggers post-call scoring and escalation.
    """
    logger.info("🔔 /status endpoint hit!")  # add this line

    form = await request.form()
    call_sid = form.get("CallSid")
    call_status = form.get("CallStatus")
    duration = int(form.get("CallDuration") or 0)
    now = datetime.now(timezone.utc)



    if not call_sid:
        logger.error("❌ Missing CallSid in Twilio status callback")
        return {"status": "missing_call_sid"}
    async with AsyncSessionLocal() as db:
        try:
            call_attempt = await db.scalar(
                select(CallAttempt).where(CallAttempt.twilio_call_sid == call_sid)
            )

            if not call_attempt:
                logger.error(f"❌ CallAttempt not found for call_sid={call_sid}")
                return {"status": "call_attempt_not_found"}

            discharge = await db.get(DischargeEvent, call_attempt.discharge_id)

            if not discharge:
                logger.error(f"❌ DischargeEvent not found for call_sid={call_sid}")
                return {"status": "discharge_not_found"}

            patient = await db.get(Patient, discharge.patient_id)

            redis_key = f"voice:call:{call_sid}"
            raw_state = await redis_client.get(redis_key)

            state = json.loads(raw_state) if raw_state else {}
            transcript = (
                state.get("transcript")
                or call_attempt.transcript
                or ""
            )


            emergency_detected = bool(state.get("emergency_detected", False))
            call_attempt.status = call_status
            call_attempt.duration_secs = duration
            call_attempt.ended_at = now
            call_attempt.transcript = transcript

            # Failed before conversation happened
            if call_status in ["failed", "busy", "no-answer", "canceled"]:
                outcome = call_status.replace("-", "_")

                call_attempt.outcome = outcome

                if discharge.call_attempt_count >= discharge.max_call_attempts:
                    discharge.call_status = "failed"
                    discharge.call_at = None
                    call_attempt.next_retry_at = None
                else:
                    retry_at = now + timedelta(minutes=30)

                    discharge.call_status = "pending"
                    discharge.call_at = retry_at

                    call_attempt.next_retry_at = retry_at

                await db.commit()
                await redis_client.delete(redis_key)

                return {"status": "retry_scheduled_or_failed", "twilio_status": call_status}
            
            # Completed call
            if call_status == "completed" and call_attempt.outcome == "no_input":
                await redis_client.delete(redis_key)
                return {"status": "already_handled_no_input"}
            if call_status == "completed":
                try:
                    call_attempt.outcome = "completed"
                    call_attempt.next_retry_at = None
                    discharge.call_status = "completed"
                    discharge.call_at = None
                    if emergency_detected:
                        result = {
                            "score": 10,
                            "tier": 3,
                            "medication_adherent": False,
                            "symptoms_worsening": True,
                            "has_followup_appointment": False,
                            "has_home_support": False,
                            "reasoning": "Emergency symptom detected during call.",
                            "emergency_detected": True,
                        }
                    else:
                        result = score_call(
                            transcript=transcript,
                            diagnosis_group=discharge.discharge_dx_group or discharge.admitting_dx,
                            baseline_risk=discharge.baseline_risk,
                        )

                    call_outcome = CallOutcome(
                        call_attempt_id=call_attempt.id,
                        risk_score=result["score"],
                        tier=result["tier"],
                        auto_escalate=result["tier"] == 3,
                        auto_escalate_reason=result["reasoning"] if result["tier"] == 3 else None,
                        recommended_action=result.get("recommended_action"),
                        needs_human_review=result["tier"] >= 2,
                        score_reasoning=result["reasoning"],
                        medication_adherent=result.get("medication_adherent", False),
                        symptoms_worsening=result.get("symptoms_worsening", False),
                        has_followup_appointment=result.get("has_followup_appointment", False),
                        has_home_support=result.get("has_home_support", False),
                        emergency_detected=result.get("emergency_detected", False),
                        flags=result.get("flags"),
                    )

                    db.add(call_outcome)
                    if patient and not state.get("emergency_escalated"):
                        route_escalation(
                            tier=result["tier"],
                            patient_name=patient.name,
                            patient_phone=patient.phone,
                            score=result["score"],
                            reasoning=result["reasoning"],
                            call_sid=call_sid,
                        )
                except Exception as e:
                    logger.error(f"❌ Scoring failed for call_sid={call_sid}: {e}")
                    discharge.call_status = "failed"
                    call_attempt.error_message = str(e)

                await db.commit()
                await redis_client.delete(redis_key)

                return {"status": "processed"}

            await db.commit()
            await redis_client.delete(redis_key)

            return {"status": "ignored_status", "twilio_status": call_status}

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Status handler error: {e}")
            return {"status": "error", "detail": str(e)}


