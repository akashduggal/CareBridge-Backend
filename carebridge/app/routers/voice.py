import os
import json
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv

from carebridge.app.services.groq_service import get_opening_message, get_ai_response, score_call
from carebridge.app.services.escalation import route_escalation

load_dotenv()

router = APIRouter(prefix="/voice", tags=["voice"])

# In-memory store for active call sessions
# { call_sid: { "patient_name": str, "diagnosis": str, "history": [], "transcript": "" } }
call_sessions = {}


@router.post("/outbound")
async def outbound_call(request: Request):
    """
    Twilio calls this when the outbound call connects.
    Returns TwiML with the opening message + first Gather.
    """
    form = await request.form()
    call_sid = form.get("CallSid")

    # E2 will pass these as URL params when initiating the call
    params = dict(request.query_params)
    patient_name = params.get("patient_name", "there")
    diagnosis = params.get("diagnosis", "your recent condition")
    patient_phone = params.get("patient_phone", "")

    # Store session
    call_sessions[call_sid] = {
        "patient_name": patient_name,
        "diagnosis": diagnosis,
        "patient_phone": patient_phone,
        "history": [],
        "transcript": ""
    }

    opening = get_opening_message(patient_name, diagnosis)

    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"{os.getenv('WEBHOOK_BASE_URL')}/voice/gather?call_sid={call_sid}",
        method="POST",
        speech_timeout="auto",
        language="en-US"
    )
    gather.say(opening, voice="Polly.Joanna")
    response.append(gather)

    # Fallback if patient doesn't speak
    response.say("I didn't catch that. We'll try again later. Goodbye.", voice="Polly.Joanna")

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
    
    session = call_sessions.get(call_sid)
    if not session:
        # Session not found, gracefully end
        response = VoiceResponse()
        response.say("Sorry, something went wrong. Goodbye.", voice="Polly.Joanna")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

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
        # Mark session for Tier 3 escalation
        session["emergency_detected"] = True
    else:
        agent_reply = get_ai_response(session["history"])

    # Append agent reply to history + transcript
    session["history"].append({"role": "assistant", "content": agent_reply})
    session["transcript"] += f"Agent: {agent_reply}\n"

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
            speech_timeout="auto",
            language="en-US"
        )
        gather.say(agent_reply, voice="Polly.Joanna")
        response.append(gather)
        # Fallback if no speech detected
        response.say("I didn't catch that, could you please repeat?", voice="Polly.Joanna")

    return Response(content=str(response), media_type="application/xml")


@router.post("/status")
async def call_status(request: Request):
    """
    Called by Twilio when call ends (status=completed).
    Triggers post-call scoring and escalation.
    """
    form = await request.form()
    call_sid = form.get("CallSid")
    call_status = form.get("CallStatus")

    if call_status != "completed":
        return {"status": "ignored"}

    session = call_sessions.get(call_sid)
    if not session:
        return {"status": "no session found"}
    print(session)
    transcript = session["transcript"]
    patient_name = session["patient_name"]
    patient_phone = session["patient_phone"]
    diagnosis = session["diagnosis"]

    # Force Tier 3 if emergency was detected mid-call
    if session.get("emergency_detected"):
        route_escalation(
            tier=3,
            patient_name=patient_name,
            patient_phone=patient_phone,
            score=10,
            reasoning="Emergency symptom detected during call (chest pain / breathing difficulty)",
            call_sid=call_sid
        )
    else:
        # Score the full transcript with Groq
        result = score_call(transcript, diagnosis)
        route_escalation(
            tier=result["tier"],
            patient_name=patient_name,
            patient_phone=patient_phone,
            score=result["score"],
            reasoning=result["reasoning"],
            call_sid=call_sid
        )

    # Clean up session from memory
    call_sessions.pop(call_sid, None)

    return {"status": "processed"}