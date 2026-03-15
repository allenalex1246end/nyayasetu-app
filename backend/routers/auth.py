"""
Authentication router: login, register, token refresh.
"""
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional

from utils.auth import (
    hash_password,
    verify_password,
    create_jwt_token,
    get_current_user,
)
from utils.validators import (
    validate_email,
    validate_password,
    validate_phone,
    get_validated_phone,
    sanitize_string,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str  # citizen, officer, auditor, admin
    phone: Optional[str] = None
    ward: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    """Register a new user (citizen, officer, etc.)."""
    from main import supabase
    
    if not supabase:
        return AuthResponse(success=False, error="Database not configured")
    
    try:
        # Validate inputs
        if not validate_email(req.email):
            return AuthResponse(success=False, error="Invalid email format")
        
        if not validate_password(req.password):
            return AuthResponse(
                success=False,
                error="Password must be at least 8 characters with uppercase, lowercase, and digit",
            )
        
        req.full_name = sanitize_string(req.full_name, max_length=255)
        if not req.full_name or len(req.full_name) < 2:
            return AuthResponse(success=False, error="Full name required (min 2 chars)")
        
        if req.role not in {"citizen", "officer", "auditor", "admin"}:
            return AuthResponse(success=False, error="Invalid role")
        
        if req.phone and not validate_phone(req.phone):
            return AuthResponse(success=False, error="Invalid phone number")
        
        # Normalize phone
        phone = get_validated_phone(req.phone)
        
        # Check if email already exists
        existing = supabase.table("users").select("id").eq("email", req.email.lower()).execute()
        if existing.data:
            return AuthResponse(success=False, error="Email already registered")
        
        # Hash password
        password_hash = hash_password(req.password)
        
        # Insert user
        user_data = {
            "email": req.email.lower(),
            "password_hash": password_hash,
            "full_name": req.full_name,
            "role": req.role.lower(),
            "phone": phone,
            "ward": req.ward if req.ward else None,
        }
        
        result = supabase.table("users").insert(user_data).execute()
        
        if not result.data:
            return AuthResponse(success=False, error="Registration failed")
        
        user = result.data[0]
        user_id = user.get("id")
        
        # Create JWT token
        token = create_jwt_token(user_id, user.get("role"), user.get("email"))
        
        logger.info("User registered: %s (role: %s)", user.get("email"), user.get("role"))
        
        return AuthResponse(
            success=True,
            data={
                "user_id": user_id,
                "email": user.get("email"),
                "role": user.get("role"),
                "full_name": user.get("full_name"),
                "token": token,
            },
        )
    
    except Exception as e:
        logger.error("Registration error: %s", str(e))
        return AuthResponse(success=False, error="Registration failed")


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Login user and return JWT token."""
    from main import supabase
    
    if not supabase:
        return AuthResponse(success=False, error="Database not configured")
    
    try:
        # Validate inputs
        if not validate_email(req.email):
            return AuthResponse(success=False, error="Invalid email format")
        
        if not req.password:
            return AuthResponse(success=False, error="Password required")
        
        # Find user by email
        result = supabase.table("users").select("*").eq("email", req.email.lower()).execute()
        
        if not result.data:
            return AuthResponse(success=False, error="Invalid email or password")
        
        user = result.data[0]
        
        # Check if active
        if not user.get("is_active", True):
            return AuthResponse(success=False, error="Account is inactive")
        
        # Verify password
        if not verify_password(req.password, user.get("password_hash", "")):
            return AuthResponse(success=False, error="Invalid email or password")
        
        # Create JWT token
        token = create_jwt_token(user.get("id"), user.get("role"), user.get("email"))
        
        logger.info("User logged in: %s (role: %s)", user.get("email"), user.get("role"))
        
        return AuthResponse(
            success=True,
            data={
                "user_id": user.get("id"),
                "email": user.get("email"),
                "role": user.get("role"),
                "full_name": user.get("full_name"),
                "ward": user.get("ward"),
                "phone": user.get("phone"),
                "token": token,
            },
        )
    
    except Exception as e:
        logger.error("Login error: %s", str(e))
        return AuthResponse(success=False, error="Login failed")


@router.get("/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current logged-in user info."""
    return {
        "success": True,
        "data": user,
        "error": None,
    }


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Logout user (frontend should discard token)."""
    logger.info("User logged out: %s", user.get("user_id"))
    return {
        "success": True,
        "data": {"message": "Logged out successfully"},
        "error": None,
    }
