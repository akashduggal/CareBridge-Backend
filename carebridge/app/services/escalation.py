import os
from twilio.rest import Client
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)
load_dotenv()

twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

FROM_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
NURSE_PHONE = os.getenv("ON_CALL_NURSE_PHONE")


def send_patient_confirmation_sms(patient_phone: str, patient_name: str):
    """Tier 1 — SMS patient confirming we got their info."""
    logger.info(
            f"Hi {patient_name}, thank you for speaking with us today. "
            f"Your care team has received your check-in. "
            f"If you have any concerns, please call your doctor directly."
        )
    # twilio_client.messages.create(
    #     to=patient_phone,
    #     from_=FROM_NUMBER,
    #     body=(
    #         f"Hi {patient_name}, thank you for speaking with us today. "
    #         f"Your care team has received your check-in. "
    #         f"If you have any concerns, please call your doctor directly."
    #     )
    # )


def notify_nurse(patient_name: str, score: int, reasoning: str, call_sid: str):
    """Tier 2 — SMS on-call nurse with patient summary."""
    logger.info(
            f"TIER 2 ALERT — Patient: {patient_name}\n"
            f"Risk Score: {score}/10\n"
            f"Reason: {reasoning}\n"
            f"Call SID: {call_sid}\n"
            f"Please review and follow up within 2 hours."
        )
    # twilio_client.messages.create(
    #     to=NURSE_PHONE,
    #     from_=FROM_NUMBER,
    #     body=(
    #         f"TIER 2 ALERT — Patient: {patient_name}\n"
    #         f"Risk Score: {score}/10\n"
    #         f"Reason: {reasoning}\n"
    #         f"Call SID: {call_sid}\n"
    #         f"Please review and follow up within 2 hours."
    #     )
    # )


def notify_physician(patient_name: str, score: int, reasoning: str, call_sid: str):
    logger.info(
            f"🚨 TIER 3 URGENT — Patient: {patient_name}\n"
            f"Risk Score: {score}/10\n"
            f"Reason: {reasoning}\n"
            f"Call SID: {call_sid}\n"
            f"IMMEDIATE physician review required."
        )
    """Tier 3 — urgent page to on-call physician."""
    # twilio_client.messages.create(
    #     to=NURSE_PHONE,
    #     from_=FROM_NUMBER,
    #     body=(
    #         f"🚨 TIER 3 URGENT — Patient: {patient_name}\n"
    #         f"Risk Score: {score}/10\n"
    #         f"Reason: {reasoning}\n"
    #         f"Call SID: {call_sid}\n"
    #         f"IMMEDIATE physician review required."
    #     )
    # )


def route_escalation(tier: int, patient_name: str, patient_phone: str,
                     score: int, reasoning: str, call_sid: str):
    """Main router — calls the right escalation based on tier."""
    logger.info(f"Routing escalation for patient {patient_name}, tier {tier}")
    if tier == 1:
        send_patient_confirmation_sms(patient_phone, patient_name)
        # pass
    elif tier == 2:
        send_patient_confirmation_sms(patient_phone, patient_name)
        notify_nurse(patient_name, score, reasoning, call_sid)
        # pass
    elif tier == 3:
        notify_physician(patient_name, score, reasoning, call_sid)
        # pass