import os
from groq import Groq
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a warm, professional post-discharge care assistant calling patients
on behalf of their hospital.

Your job is to ask general post-discharge check-in questions.

Assess:
1. Medication adherence
2. New or worsening symptoms
3. Follow-up appointment
4. Support at home

Rules:
- Do not mention diagnosis, condition name, hospital details, or medications by name.
- Never diagnose.
- Never give medical advice except emergency guidance.
- Ask ONE question at a time.
- Keep each response under 3 sentences.
- If the patient mentions chest pain, difficulty breathing, stroke symptoms, or loss of consciousness,
  tell them to call 911 or go to the nearest emergency room.
- When enough information is collected, end with:
  "Thank you so much for your time. We'll follow up if needed. Take care and feel better soon. Goodbye."
"""


def get_opening_message(patient_name: str) -> str:
    """Returns the opening line of the call."""
    return (
        f"Hello, may I speak with {patient_name}? "
        f"This is a care follow-up call from your hospital. "
        f"You were recently discharged and we just want to check in on how you're doing. "
        f"Is now a good time to talk?"
    )

def get_ai_response(conversation_history: list, baseline_risk: str = "medium") -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Baseline risk: {baseline_risk}. Do not mention diagnosis."},
            *conversation_history
        ],
        max_tokens=150,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

def score_call(transcript: str, diagnosis_group: str, baseline_risk: str) -> dict:
    """After call ends, score the patient's risk level. Returns tier + reasoning."""
    if len(transcript.strip()) < 20:
        return {
            "score": 0,
            "tier": 1,
            "medication_adherent": True,
            "symptoms_worsening": False,
            "has_followup_appointment": False,
            "has_home_support": False,
            "reasoning": "Call too short to score accurately",
            "emergency_detected": False
        }
    scoring_prompt = f"""
You are a clinical triage assistant. Based on the following post-discharge call transcript, 
score the patient's readmission risk.

Diagnosis group: {diagnosis_group}
Baseline risk: {baseline_risk}
Transcript:
{transcript}

Return a JSON object with exactly these fields:
- score: integer 0-10 (0 = low risk, 10 = critical)
- tier: integer 1, 2, or 3
  (Tier 1 = score 0-3, routine. Tier 2 = score 4-6, nurse follow-up needed. Tier 3 = score 7-10, urgent escalation)
- medication_adherent: boolean
- symptoms_worsening: boolean  
- has_followup_appointment: boolean
- has_home_support: boolean
- reasoning: string (1 sentence explaining the score)
- emergency_detected: boolean (true if patient mentioned chest pain, difficulty breathing, or similar)

Respond with ONLY the JSON object, no other text.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": scoring_prompt}],
        max_tokens=300,
        temperature=0.1,
    )
    import json
    raw = response.choices[0].message.content.strip()
    logger.info(f"Raw scoring response: {raw}")
    # Strip any markdown backtick wrapping
    if raw.startswith("```"):
        # Remove opening ``` and optional language tag
        raw = raw.lstrip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        # Remove closing ```
        raw = raw.rstrip("`")

    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Groq returned invalid JSON: {raw}") from e