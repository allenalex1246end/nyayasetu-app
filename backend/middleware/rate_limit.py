"""
Rate limiting middleware using slowapi.
"""
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Initialize limiter with IP-based rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


def add_rate_limiting(app: FastAPI):
    """Add rate limiting to FastAPI app."""
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        """Custom handler for rate limit exceeded."""
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "data": None,
                "error": "Rate limit exceeded. Please try again later.",
                "retry_after": exc.detail.split("calls in ")[-1] if exc.detail else "unknown",
            },
        )
    
    # Return configured limiter
    return limiter
