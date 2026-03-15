import os
import json
import logging
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import numpy as np

from utils.groq_client import analyse_grievance, generate_brief, translate_to_malayalam, translate_from_malayalam, explain_436a, call_groq
from utils.gemini_client import get_embedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["AI"])


# --- Request/Response models ---

class AnalyseRequest(BaseModel):
    text: str
    ward: str = "Unknown"

class BriefRequest(BaseModel):
    clusters: list

class EmbedRequest(BaseModel):
    text: str

class ExtractIdentityRequest(BaseModel):
    transcript: str


# --- Fast local identity extraction (regex-based) ---
def extract_identity_fast(transcript: str) -> dict:
    """Fast regex-based extraction of name and phone from transcript.
    
    Uses intelligent regex patterns to extract names and phone numbers instantly.
    Falls back to Groq only if regex finds nothing.
    """
    name = ""
    phone = ""
    
    if not transcript or not isinstance(transcript, str):
        return {"name": "", "phone": ""}
    
    # Normalize transcript for better matching
    normalized = transcript.lower()
    
    # ===== PHONE EXTRACTION (more lenient patterns) =====
    phone_patterns = [
        # Indian format with country code
        r'\+91[\s-]?([6-9]\d{3}[\s-]?\d{6})',      # +91 9XXXXXXXXX
        r'\+91[\s-]?([6-9]\d{9})',                  # +91 9XXXXXXXXX (no separators)
        # Indian format without country code  
        r'\b([6-9]\d{3}[\s-]?\d{6})\b',             # 9XXXXXXXXX
        r'\b([6-9]\d{9})\b',                        # 9XXXXXXXXX (continuous)
        # International formats
        r'\b(\d{3})[\s.-]?(\d{3})[\s.-]?(\d{4})\b', # XXX-XXX-XXXX
        r'\+(\d{1,3})[\s-]?(\d{8,14})',             # +country code
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, transcript)
        if match:
            phone_str = re.sub(r'[\s\-().]', '', match.group(0))
            digits_only = re.sub(r'\D', '', phone_str)
            if len(digits_only) >= 10:
                phone = phone_str
                break
    
    # ===== NAME EXTRACTION (intelligent patterns in order) =====
    
    # Pattern 1: "My name is [Name]" / "My name's [Name]"
    if not name:
        match = re.search(
            r"(?:my name is|my name's|my name's|my name was)\s+([a-z][a-z]+(?:\s+[a-z][a-z]+){0,2})",
            normalized
        )
        if match:
            name = match.group(1).title()
    
    # Pattern 2: "I am [Name]" / "I'm [Name]" / "I am called [Name]"
    if not name:
        match = re.search(
            r"(?:i am|i'm|i am called|i'm called)\s+([a-z][a-z]+(?:\s+[a-z][a-z]+){0,2})",
            normalized
        )
        if match:
            name = match.group(1).title()
    
    # Pattern 3: "This is [Name]"
    if not name:
        match = re.search(
            r"this is\s+([a-z][a-z]+(?:\s+[a-z][a-z]+){0,2})",
            normalized
        )
        if match:
            name = match.group(1).title()
    
    # Pattern 4: "[Name] here/speaking/calling/on the line"
    if not name:
        match = re.search(
            r"([a-z][a-z]+(?:\s+[a-z][a-z]+){0,2})\s+(?:here|speaking|calling|is speaking)",
            normalized
        )
        if match:
            name = match.group(1).title()
    
    # Pattern 5: "Call me [Name]"
    if not name:
        match = re.search(
            r"(?:call me|you can call me)\s+([a-z][a-z]+(?:\s+[a-z][a-z]+){0,2})",
            normalized
        )
        if match:
            name = match.group(1).title()
    
    # Pattern 6: "[Name] is my name"
    if not name:
        match = re.search(
            r"([a-z][a-z]+(?:\s+[a-z][a-z]+){0,2})\s+is my name",
            normalized
        )
        if match:
            name = match.group(1).title()
    
    # Pattern 7: Start of sentence - capitalized names "Hello [Name], I want to report..."
    if not name:
        # Look for capitalized proper nouns that appear to be names (not at sentence start)
        matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,1})\b", transcript)
        if matches:
            # Filter out common words
            excluded_words = {'i', 'a', 'the', 'please', 'help', 'need', 'my', 'this', 'is', 'district', 'ward'}
            for match_name in matches:
                if match_name.lower() not in excluded_words and len(match_name) > 2:
                    name = match_name
                    break
    
    # Pattern 8: Hindi/regional pattern - "Mera naam [Name] hai"
    if not name:
        match = re.search(
            r"(?:mera naam|mere naam)\s+([a-z][a-z]+(?:\s+[a-z][a-z]+){0,2})",
            normalized
        )
        if match:
            name = match.group(1).title()
    
    # Pattern 9: "[Name] speaking from [location]"
    if not name:
        match = re.search(
            r"([a-z][a-z]+(?:\s+[a-z][a-z]+){0,1})\s+speaking\s+from",
            normalized
        )
        if match:
            name = match.group(1).title()
    
    # ===== NAME CLEANUP =====
    if name:
        # Remove common filler words that shouldn't be part of name
        filler_pattern = r'\b(the|my|and|or|a|an|is|are|from|called)\b'
        name = re.sub(filler_pattern, '', name, flags=re.IGNORECASE).strip()
        
        # Remove extra spaces
        name = ' '.join(name.split())
        
        # Ensure minimum requirements (2+ chars, not just noise)
        if len(name) < 2 or name.lower() in ['hi', 'ok', 'yeah', 'yes', 'no', 'hello']:
            name = ""
    
    return {"name": name, "phone": phone}


# --- Endpoints ---

@router.post("/analyse")
async def analyse_endpoint(req: AnalyseRequest):
    """Analyse a grievance with Groq AI."""
    try:
        result = await analyse_grievance(req.text, req.ward)
        return {"success": True, "data": result, "error": None}
    except Exception as e:
        logger.error("Analyse endpoint error: %s", str(e))
        return {
            "success": False,
            "data": {
                "category": "other",
                "urgency": 3,
                "credibility_score": 50,
                "summary": req.text[:50] if req.text else "No description",
                "department": "General Administration",
            },
            "error": str(e),
        }


@router.post("/brief")
async def brief_endpoint(req: BriefRequest):
    """Generate governance intelligence brief."""
    try:
        result = await generate_brief(req.clusters)
        return {"success": True, "data": {"brief": result}, "error": None}
    except Exception as e:
        logger.error("Brief endpoint error: %s", str(e))
        return {"success": False, "data": None, "error": str(e)}


@router.post("/embed")
async def embed_endpoint(req: EmbedRequest):
    """Get embedding for text (internal use)."""
    try:
        embedding = await get_embedding(req.text)
        if embedding is None:
            return {"success": False, "data": None, "error": "Failed to get embedding"}
        return {"success": True, "data": {"embedding": embedding}, "error": None}
    except Exception as e:
        logger.error("Embed endpoint error: %s", str(e))
        return {"success": False, "data": None, "error": str(e)}


@router.post("/extract-identity")
async def extract_identity(req: ExtractIdentityRequest):
    """Extract name and phone number from voice transcript using fast regex first, then Groq."""
    try:
        # FAST LOCAL EXTRACTION (instant)
        fast_result = extract_identity_fast(req.transcript)
        
        # If we found both, return immediately
        if fast_result["name"] and fast_result["phone"]:
            return {
                "success": True,
                "data": fast_result,
                "error": None,
                "method": "fast_local"
            }
        
        # If we found at least one, return (don't wait for slow Groq)
        if fast_result["name"] or fast_result["phone"]:
            return {
                "success": True,
                "data": fast_result,
                "error": None,
                "method": "fast_local"
            }
        
        # FALLBACK: Use Groq for more complex cases (slower but more accurate)
        prompt = (
            "Extract the person's name and phone number from this spoken text. "
            "Return ONLY valid JSON with no explanation or markdown:\n"
            '{"name": "<extracted full name or empty string>", "phone": "<extracted phone number or empty string>"}\n'
            "Rules:\n"
            "- If no name is found, return empty string for name\n"
            "- If no phone is found, return empty string for phone\n"
            "- Phone should include country code if mentioned (e.g. +91)\n"
            "- Clean up the phone to digits and + only\n"
            f"\nTranscript: {req.transcript}"
        )
        raw = await call_groq(prompt)
        if not raw:
            return {"success": True, "data": {"name": "", "phone": ""}, "error": None, "method": "groq_empty"}

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result = json.loads(cleaned)
        return {
            "success": True,
            "data": {
                "name": result.get("name", ""),
                "phone": result.get("phone", ""),
            },
            "error": None,
            "method": "groq"
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return {"success": True, "data": {"name": "", "phone": ""}, "error": None, "method": "error_json"}
    except Exception as e:
        logger.error("Extract identity error: %s", str(e))
        return {"success": True, "data": {"name": "", "phone": ""}, "error": str(e), "method": "error"}


def cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    try:
        a_arr = np.array(a, dtype=np.float64)
        b_arr = np.array(b, dtype=np.float64)
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))
    except Exception:
        return 0.0


@router.post("/cluster")
async def cluster_endpoint():
    """Run cluster detection on unclustered open grievances."""
    from main import supabase
    from utils.clustering import cluster_grievances
    from utils.gemini_client import GемiniClient
    from utils.groq_client import GroqClient
    
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    
    try:
        # Fetch open grievances without cluster_id
        result = supabase.table("grievances").select("*").eq("status", "open").is_("cluster_id", "null").execute()
        grievances = result.data or []

        if len(grievances) < 2:
            return {
                "success": True,
                "data": {"clusters_created": 0, "grievances_clustered": 0, "message": "Not enough unclustered grievances"},
                "error": None,
            }

        # Initialize AI clients
        gemini_client = GемiniClient()
        groq_client = GroqClient()
        
        # Run clustering
        clusters_created, grievances_clustered = await cluster_grievances(
            grievances,
            gemini_client,
            supabase,
            table_name="grievances",
            cluster_table="clusters",
        )

        return {
            "success": True,
            "data": {
                "clusters_created": clusters_created,
                "grievances_clustered": grievances_clustered,
            },
            "error": None,
        }
    except Exception as e:
        logger.error("Cluster endpoint error: %s", str(e))
        return {"success": False, "data": None, "error": str(e)}


@router.get("/translate/{grievance_id}")
async def translate_endpoint(grievance_id: str):
    """Translate grievance summary to Malayalam."""
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        result = supabase.table("grievances").select("ai_summary, description").eq("id", grievance_id).execute()
        if not result.data:
            return {"success": False, "data": None, "error": "Grievance not found"}

        grievance = result.data[0]
        text = grievance.get("ai_summary") or grievance.get("description", "")
        if not text:
            return {"success": False, "data": None, "error": "No text to translate"}

        translated = await translate_to_malayalam(text)
        return {"success": True, "data": {"original": text, "malayalam": translated}, "error": None}
    except Exception as e:
        logger.error("Translate endpoint error: %s", str(e))
        return {"success": False, "data": None, "error": str(e)}


class TranslateRequest(BaseModel):
    text: str


@router.post("/translate-from-malayalam")
async def translate_from_malayalam_endpoint(req: TranslateRequest):
    """Translate text from Malayalam to English."""
    try:
        if not req.text or not req.text.strip():
            return {"success": False, "data": None, "error": "No text provided"}
        
        translated = await translate_from_malayalam(req.text)
        return {"success": True, "data": {"original": req.text, "english": translated}, "error": None}
    except Exception as e:
        logger.error("Translate from Malayalam endpoint error: %s", str(e))
        return {"success": False, "data": None, "error": str(e)}
