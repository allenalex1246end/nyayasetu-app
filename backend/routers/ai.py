import os
import json
import logging
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
    """Extract name and phone number from voice transcript using Groq."""
    try:
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
            return {"success": True, "data": {"name": "", "phone": ""}, "error": None}

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
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return {"success": True, "data": {"name": "", "phone": ""}, "error": None}
    except Exception as e:
        logger.error("Extract identity error: %s", str(e))
        return {"success": True, "data": {"name": "", "phone": ""}, "error": str(e)}


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
