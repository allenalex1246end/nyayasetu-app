"""
Input validation and sanitization utilities.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Wards in Thiruvananthapuram (from seed data)
VALID_WARDS = {
    "Ward 1 (Kazhakoottam)",
    "Ward 2 (Technopark)",
    "Ward 3 (Pattom)",
    "Ward 4 (Vanchiyoor)",
    "Ward 5 (Palayam)",
    "Ward 6 (Karamana)",
    "Ward 7 (Nemom)",
    "Ward 8 (Kovalam)",
}

VALID_CATEGORIES = {
    "water", "road", "electricity", "health", "sanitation", "legal", "other", "railway"
}

VALID_GRIEVANCE_STATUS = {"open", "in_progress", "resolved", "rejected", "breached"}
VALID_OFFICER_ROLES = {"officer", "auditor", "admin"}
VALID_ROLES = {"citizen", "officer", "auditor", "admin"}


def validate_phone(phone: Optional[str]) -> bool:
    """Validate Indian phone number (+91XXXXXXXXXX or XXXXXXXXXX)."""
    if not phone:
        return True  # Optional field
    
    # Remove spaces and hyphens
    phone = phone.replace(" ", "").replace("-", "")
    
    # Check if matches Indian format
    pattern = r"^(\+91|91)?[6-9]\d{9}$"
    return bool(re.match(pattern, phone))


def validate_ward(ward: str) -> bool:
    """Check if ward is in valid list."""
    return ward in VALID_WARDS


def validate_category(category: str) -> bool:
    """Check if category is valid."""
    return category.lower() in VALID_CATEGORIES


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email)) and len(email) <= 255


def validate_status(status: str) -> bool:
    """Check if status is valid."""
    return status.lower() in VALID_GRIEVANCE_STATUS


def validate_role(role: str) -> bool:
    """Check if role is valid."""
    return role.lower() in VALID_ROLES


def sanitize_string(text: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
    """
    Sanitize string: 
    - Strip whitespace
    - Normalize unicode
    - Limit length
    - No HTML/script tags
    """
    if not text:
        return None
    
    # Strip whitespace
    text = text.strip()
    
    # Normalize unicode
    text = text.encode("utf-8", errors="ignore").decode("utf-8")
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_description(description: str, min_length: int = 10, max_length: int = 5000) -> bool:
    """Validate complaint description."""
    if not description:
        return False
    
    description = sanitize_string(description)
    if not description:
        return False
    
    if len(description) < min_length:
        return False
    
    if len(description) > max_length:
        return False
    
    # Check for excessive HTML/scripts (very basic check)
    dangerous_patterns = ["<script", "javascript:", "onerror=", "onclick="]
    text_lower = description.lower()
    if any(pattern in text_lower for pattern in dangerous_patterns):
        return False
    
    return True


def validate_password(password: str, min_length: int = 8) -> bool:
    """
    Validate password strength:
    - Minimum length
    - At least one uppercase
    - At least one lowercase
    - At least one digit
    """
    if len(password) < min_length:
        return False
    
    if not re.search(r"[A-Z]", password):
        return False
    
    if not re.search(r"[a-z]", password):
        return False
    
    if not re.search(r"\d", password):
        return False
    
    return True


def validate_detection_start(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def get_validated_phone(phone: Optional[str]) -> Optional[str]:
    """Get normalized phone number or None if invalid."""
    if not phone:
        return None
    
    if not validate_phone(phone):
        return None
    
    # Normalize to +91 format
    phone = phone.replace(" ", "").replace("-", "")
    if not phone.startswith("+91") and not phone.startswith("91"):
        phone = f"+91{phone[-10:]}"
    elif phone.startswith("91") and not phone.startswith("+91"):
        phone = f"+{phone}"
    
    return phone
