import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a warm, professional post-discharge care assistant calling patients 
on behalf of their hospital. Your job is to check in on the patient after they were recently discharged.

You must assess:
1. Medication adherence — are they taking all medications as prescribed?
2. Symptom changes — any new or worsening symptoms since discharge?
3. Follow-up appointment — have they scheduled or confirmed it?
4. Support at home — do they have help at home?

Rules:
- Be warm, concise, and clear. Patients may be elderly or unwell.
- Ask ONE question at a time.
- If the patient mentions chest pain, difficulty breathing, or any emergency symptom, 
  immediately say: "That sounds serious. Please call 911 or go to your nearest emergency room right away."
- Never diagnose. Never give medical advice beyond directing to emergency services.
- Keep each response under 3 sentences.
- When you have enough information on all 4 areas, end with: "Thank you so much for your time. 
  We'll follow up if needed. Take care and feel better soon. Goodbye."
"""

def get_opening_message(patient_name: str, diagnosis: str) -> str:
    """Returns the opening line of the call."""
    return (
        f"Hello, may I speak with {patient_name}? "
        f"This is a care follow-up call from your hospital. "
        f"You were recently discharged and we just want to check in on how you're doing. "
        f"Is now a good time to talk?"
    )

def get_ai_response(conversation_history: list) -> str:
    """Send conversation history to Groq and get next agent response."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *conversation_history
        ],
        max_tokens=150,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

def score_call(transcript: str, diagnosis_group: str) -> dict:
    """After call ends, score the patient's risk level. Returns tier + reasoning."""
    scoring_prompt = f"""
You are a clinical triage assistant. Based on the following post-discharge call transcript, 
score the patient's readmission risk.

Diagnosis group: {diagnosis_group}
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
    return json.loads(raw)