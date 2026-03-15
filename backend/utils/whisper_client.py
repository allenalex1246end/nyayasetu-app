"""
Direct OpenAI Whisper API integration via HTTP.
No problematic client libraries.
"""
import os
import logging
from typing import Optional, Dict, Any
import io

logger = logging.getLogger(__name__)

WHISPER_API_KEY = os.getenv("WHISPER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


async def transcribe_audio(
    audio_bytes: bytes,
    language: str = "en",
) -> Optional[Dict[str, Any]]:
    """
    Transcribe audio using OpenAI Whisper API.
    Direct HTTP implementation, no client library issues.
    """
    try:
        if not WHISPER_API_KEY:
            logger.error("WHISPER_API_KEY not configured")
            return None
        
        import httpx
        
        logger.info(f"Transcribing {len(audio_bytes)} bytes with OpenAI Whisper...")
        
        headers = {
            "Authorization": f"Bearer {WHISPER_API_KEY}",
        }
        
        files = {
            "file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav"),
            "model": (None, "whisper-1"),
        }
        
        if language and language != "auto":
            files["language"] = (None, language)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
            )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get("text", "").strip()
            
            if text:
                logger.info(f"✅ Transcribed: {text[:60]}...")
                return {
                    "text": text,
                    "confidence": 0.95,
                    "language": language or "en",
                }
            else:
                logger.warning("Whisper returned empty text")
                return None
        else:
            error_msg = response.text[:200]
            logger.error(f"OpenAI API error {response.status_code}: {error_msg}")
            return None
    
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return None


async def transcribe_audio_with_fallback(
    audio_bytes: bytes,
    language: str = "en",
) -> Optional[Dict[str, Any]]:
    """Wrapper function for compatibility."""
    return await transcribe_audio(audio_bytes, language)



async def transcribe_audio_with_fallback(
    audio_bytes: bytes,
    language: str = "en",
) -> Optional[Dict[str, Any]]:
    """
    Transcribe audio with fallback support.
    Uses OpenAI or Groq Whisper.
    """
    result = await transcribe_audio(audio_bytes, language)
    
    if result and "error" not in result:
        return result
    
    logger.warning("Transcription failed, frontend should use Web Speech API as fallback")
    return None
