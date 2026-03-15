"""
Twilio SMS integration for NyayaSetu notifications.
- Grievance submission confirmations
- Officer assignment notifications
- Status update alerts
"""
import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def get_twilio_client():
    """Initialize Twilio client if credentials are configured."""
    try:
        from twilio.rest import Client as TwilioClient
        
        sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        
        # Check if credentials are configured and not using placeholder values
        if sid and token and from_number and sid != "your_twilio_sid":
            return TwilioClient(sid, token), from_number
    except ImportError:
        logger.warning("Twilio package not installed. Continue without SMS.")
    except Exception as e:
        logger.error("Failed to initialize Twilio: %s", str(e))
    
    return None, None


def send_sms(phone_number: str, message: str) -> Tuple[bool, str]:
    """
    Send SMS via Twilio.
    
    Args:
        phone_number: Recipient phone number (format: +91XXXXXXXXXX)
        message: SMS message content
    
    Returns:
        (success: bool, message: str) - Success status and detail message
    """
    if not phone_number:
        return False, "No phone number provided"
    
    # Normalize phone number
    phone = phone_number.strip()
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")
    
    twilio_client, from_number = get_twilio_client()
    
    if not twilio_client or not from_number:
        logger.info(
            "Twilio not configured. Would send SMS to %s: %s",
            phone,
            message[:50]
        )
        return False, "SMS service not configured"
    
    try:
        response = twilio_client.messages.create(
            body=message,
            from_=from_number,
            to=phone
        )
        logger.info("SMS sent to %s (SID: %s)", phone, response.sid)
        return True, f"SMS sent (SID: {response.sid})"
    except Exception as e:
        logger.error("Failed to send SMS to %s: %s", phone, str(e))
        return False, f"SMS failed: {str(e)}"


def send_grievance_confirmation(phone_number: str, grievance_id: str, tracking_url: str = None) -> Tuple[bool, str]:
    """
    Send SMS confirmation when grievance is submitted.
    Format: "Your complaint #{ID} received. Category: {Category}. Track at: {URL}"
    """
    url_text = f"Track: {tracking_url}" if tracking_url else "Check your email for details"
    message = f"ನ್ಯಾಯ ಸೇತು: Your complaint #{grievance_id[:8].upper()} received. {url_text}"
    return send_sms(phone_number, message)


def send_assignment_notification(officer_phone: str, grievance_category: str, citizen_name: str, ward: str) -> Tuple[bool, str]:
    """
    Send SMS notification to officer when grievance is assigned.
    Format: "New complaint: {Category} from {Name} in {Ward}. Check dashboard."
    """
    message = f"ನ್ಯಾಯ ಸೇತು (NyayaSetu): New complaint ({grievance_category}) from {citizen_name} in {ward}. Check dashboard."
    return send_sms(officer_phone, message)


def send_status_update_notification(citizen_phone: str, grievance_id: str, new_status: str, tracking_url: str = None) -> Tuple[bool, str]:
    """
    Send SMS when grievance status is updated.
    Format: "Complaint #{ID} status: {Status}. {URL or contact info}"
    """
    status_text = {
        "in_progress": "In Progress",
        "resolved": "Resolved",
        "rejected": "Rejected",
        "pending_confirmation": "Awaiting Confirmation"
    }.get(new_status, new_status.replace("_", " ").title())
    
    url_text = f"Details: {tracking_url}" if tracking_url else ""
    message = f"ನ್ಯಾಯ ಸೇತು: Complaint #{grievance_id[:8].upper()} → {status_text}. {url_text}"
    return send_sms(citizen_phone, message)


def send_sla_warning(officer_phone: str, grievance_id: str, hours_remaining: int) -> Tuple[bool, str]:
    """
    Send SMS warning to officer when SLA breach is imminent.
    Format: "⚠️ Complaint #{ID} SLA: {Hours} hours remaining. Take action now."
    """
    message = f"⚠️ ನ್ಯಾಯ ಸೇತು: Complaint #{grievance_id[:8].upper()} SLA: {hours_remaining}h remaining. Act now!"
    return send_sms(officer_phone, message)


def send_resolution_confirmation_prompt(citizen_phone: str, grievance_id: str, resolution_url: str = None) -> Tuple[bool, str]:
    """
    Send SMS asking citizen to confirm resolution.
    Format: "Complaint #{ID} resolved? Reply YES to confirm or NO to reopen."
    """
    url_text = f"Confirm: {resolution_url}" if resolution_url else "Reply YES/NO"
    message = f"ನ್ಯಾಯ ಸೇತು: Complaint #{grievance_id[:8].upper()} marked resolved. {url_text}"
    return send_sms(citizen_phone, message)


def send_bulk_sms(recipients: list, message: str) -> dict:
    """
    Send SMS to multiple recipients.
    
    Args:
        recipients: List of phone numbers
        message: SMS message content
    
    Returns:
        dict with stats: {sent: int, failed: int, results: []}
    """
    stats = {"sent": 0, "failed": 0, "results": []}
    
    for phone in recipients:
        success, detail = send_sms(phone, message)
        stats["results"].append({"phone": phone, "success": success, "detail": detail})
        if success:
            stats["sent"] += 1
        else:
            stats["failed"] += 1
    
    return stats
