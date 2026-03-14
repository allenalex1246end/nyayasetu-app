import os
import json
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
GEMINI_VISION_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
GEMINI_TIMEOUT = 15.0
GEMINI_VISION_TIMEOUT = 30.0


async def get_embedding(text: str) -> list | None:
    """Get 768-dimension embedding from Gemini text-embedding-004. Returns None on failure."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_key":
        logger.warning("Gemini API key not configured, skipping embedding")
        return None

    if not text or not text.strip():
        return None

    url = f"{GEMINI_EMBED_URL}?key={GEMINI_API_KEY}"
    payload = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": text[:2048]}]
        },
    }

    try:
        async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", {}).get("values", None)
            if embedding and len(embedding) > 0:
                return embedding
            logger.error("Gemini returned empty embedding")
            return None
    except httpx.TimeoutException:
        logger.error("Gemini embedding API timeout after %.1fs", GEMINI_TIMEOUT)
        return None
    except httpx.HTTPStatusError as e:
        logger.error("Gemini embedding HTTP error: %s %s", e.response.status_code, e.response.text[:200])
        return None
    except Exception as e:
        logger.error("Gemini embedding unexpected error: %s", str(e))
        return None


async def verify_with_image(description: str, image_base64: str) -> dict:
    """Use Gemini Vision to cross-reference an image with complaint text description.
    Returns verification result with severity adjustment and fake risk assessment."""
    safe_defaults = {
        "verified": True,
        "severity_adjustment": 0,
        "image_description": "",
        "fake_risk": False,
    }

    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_key":
        logger.warning("Gemini API key not configured, skipping image verification")
        return safe_defaults

    if not image_base64:
        return safe_defaults

    url = f"{GEMINI_VISION_URL}?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [
                {
                    "text": (
                        "You are a grievance verification AI for India. Analyse this image alongside the complaint description. "
                        "Return ONLY valid JSON with no explanation or markdown:\n"
                        '{"verified": <true if image matches complaint description, false otherwise>, '
                        '"severity_adjustment": <integer from -2 to +2 to adjust urgency based on image evidence>, '
                        '"image_description": "<brief description of what the image shows>", '
                        '"fake_risk": <true if image appears unrelated/fake/stock photo, false otherwise>}\n'
                        f"\nComplaint description: {description[:500]}"
                    ),
                },
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_base64,
                    },
                },
            ],
        }],
    }

    try:
        async with httpx.AsyncClient(timeout=GEMINI_VISION_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not text:
                return safe_defaults

            cleaned = text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            result = json.loads(cleaned)
            return {
                "verified": result.get("verified", True),
                "severity_adjustment": int(result.get("severity_adjustment", 0)),
                "image_description": result.get("image_description", ""),
                "fake_risk": result.get("fake_risk", False),
            }
    except httpx.TimeoutException:
        logger.error("Gemini Vision API timeout after %.1fs", GEMINI_VISION_TIMEOUT)
        return safe_defaults
    except httpx.HTTPStatusError as e:
        logger.error("Gemini Vision HTTP error: %s %s", e.response.status_code, e.response.text[:200])
        return safe_defaults
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.error("Failed to parse Gemini Vision response: %s", str(e))
        return safe_defaults
    except Exception as e:
        logger.error("Gemini Vision unexpected error: %s", str(e))
        return safe_defaults
