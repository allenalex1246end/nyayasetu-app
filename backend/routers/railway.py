import logging
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import numpy as np

from utils.hashing import generate_hash, generate_action_hash
from utils.groq_client import analyse_railway_grievance, generate_brief
from utils.gemini_client import get_embedding, verify_with_image
from utils.db_helpers import is_table_missing

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/railway", tags=["Railway"])


# --- Domain Data ---

RAILWAY_ZONES = [
    "Southern Railway",
    "Northern Railway",
    "Eastern Railway",
    "Western Railway",
    "Central Railway",
    "South Central Railway",
    "South Eastern Railway",
    "South Western Railway",
    "North Central Railway",
    "North Eastern Railway",
    "North Western Railway",
    "Northeast Frontier Railway",
    "East Central Railway",
    "East Coast Railway",
    "West Central Railway",
    "Konkan Railway",
    "Metro Railway Kolkata",
]

RAILWAY_CATEGORIES = [
    "cleanliness", "catering", "punctuality", "safety",
    "electrical", "water", "staff_behavior", "overcrowding", "other",
]


# --- Models ---

class RailwayGrievanceCreate(BaseModel):
    passenger_name: str
    phone: Optional[str] = None
    train_number: str
    railway_zone: str
    station: Optional[str] = None
    coach_number: Optional[str] = None
    description: str
    category: Optional[str] = None
    image_data: Optional[str] = None


# --- Helpers ---

def log_railway_action(supabase, grievance_id: str, action_type: str, performed_by: str = "system", notes: str = ""):
    try:
        action_data = {
            "grievance_id": grievance_id,
            "action_type": action_type,
            "performed_by": performed_by,
            "notes": notes,
        }
        result = supabase.table("railway_actions").insert(action_data).execute()
        if result.data:
            action = result.data[0]
            action_hash = generate_action_hash(
                action.get("id", ""),
                grievance_id,
                action_type,
                action.get("created_at", ""),
            )
            supabase.table("railway_actions").update({"hash": action_hash}).eq("id", action["id"]).execute()
    except Exception as e:
        logger.error("Failed to log railway action: %s", str(e))


def cosine_similarity(a: list, b: list) -> float:
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


# --- CRUD Endpoints ---

@router.post("/grievances")
async def create_railway_grievance(req: RailwayGrievanceCreate):
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        analysis = await analyse_railway_grievance(req.description, req.train_number, req.railway_zone)
        urgency = analysis.get("urgency", 3)

        # Image verification
        image_url = None
        image_verified = None
        image_analysis = None
        if req.image_data:
            image_analysis = await verify_with_image(req.description, req.image_data)
            image_url = f"data:image/jpeg;base64,{req.image_data[:100]}..."
            image_verified = image_analysis.get("verified", True)
            adjustment = image_analysis.get("severity_adjustment", 0)
            urgency = max(1, min(5, urgency + adjustment))

        grievance_data = {
            "passenger_name": req.passenger_name,
            "phone": req.phone,
            "train_number": req.train_number,
            "railway_zone": req.railway_zone,
            "station": req.station,
            "coach_number": req.coach_number,
            "description": req.description,
            "category": req.category or analysis.get("category", "other"),
            "urgency": urgency,
            "credibility_score": analysis.get("credibility_score", 50),
            "ai_summary": analysis.get("summary", req.description[:50]),
            "status": "open",
            "image_url": image_url,
            "image_verified": image_verified,
        }
        result = supabase.table("railway_grievances").insert(grievance_data).execute()
        if not result.data:
            return {"success": False, "data": None, "error": "Failed to insert railway grievance"}

        grievance = result.data[0]
        gid = grievance["id"]
        hash_val = generate_hash(gid, grievance.get("created_at", ""), req.description)
        supabase.table("railway_grievances").update({"hash": hash_val}).eq("id", gid).execute()
        log_railway_action(supabase, gid, "submitted", performed_by="passenger",
                           notes=f"Railway complaint submitted by {req.passenger_name}")
        grievance["hash"] = hash_val
        return {
            "success": True,
            "data": {"grievance": grievance, "hash": hash_val, "ai_analysis": analysis, "image_analysis": image_analysis},
            "error": None,
        }
    except Exception as e:
        logger.error("Create railway grievance error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": False, "data": None, "error": "Railway tables not created yet. Run V2 schema SQL in Supabase SQL Editor."}
        return {"success": False, "data": None, "error": str(e)}


@router.get("/grievances")
async def get_railway_grievances(
    status: Optional[str] = None,
    category: Optional[str] = None,
    train_number: Optional[str] = None,
    railway_zone: Optional[str] = None,
    limit: int = 50,
):
    from main import supabase
    if not supabase:
        return {"success": False, "data": [], "error": "Database not configured"}
    try:
        query = supabase.table("railway_grievances").select("*")
        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)
        if train_number:
            query = query.eq("train_number", train_number)
        if railway_zone:
            query = query.eq("railway_zone", railway_zone)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return {"success": True, "data": result.data or [], "error": None}
    except Exception as e:
        logger.error("Get railway grievances error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": True, "data": [], "error": None}
        return {"success": False, "data": [], "error": str(e)}


@router.get("/grievances/{grievance_id}")
async def get_railway_grievance(grievance_id: str):
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        g_result = supabase.table("railway_grievances").select("*").eq("id", grievance_id).execute()
        if not g_result.data:
            return {"success": False, "data": None, "error": "Railway grievance not found"}
        a_result = supabase.table("railway_actions").select("*").eq("grievance_id", grievance_id).order("created_at", desc=False).execute()
        return {
            "success": True,
            "data": {"grievance": g_result.data[0], "actions": a_result.data or []},
            "error": None,
        }
    except Exception as e:
        logger.error("Get railway grievance error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": False, "data": None, "error": "Railway tables not created yet."}
        return {"success": False, "data": None, "error": str(e)}


@router.patch("/grievances/{grievance_id}/resolve")
async def resolve_railway_grievance(grievance_id: str):
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("railway_grievances").update({"status": "resolved", "resolved_at": now}).eq("id", grievance_id).execute()
        log_railway_action(supabase, grievance_id, "resolved", performed_by="officer", notes="Marked resolved by railway officer")
        return {
            "success": True,
            "data": {"message": "Railway grievance resolved"},
            "error": None,
        }
    except Exception as e:
        logger.error("Resolve railway grievance error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": False, "data": None, "error": "Railway tables not created yet."}
        return {"success": False, "data": None, "error": str(e)}


# --- Clustering ---

@router.post("/cluster")
async def railway_cluster_endpoint():
    """Run cluster detection on unclustered open railway grievances."""
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        result = supabase.table("railway_grievances").select("*").eq("status", "open").is_("cluster_id", "null").execute()
        grievances = result.data or []

        if len(grievances) < 2:
            return {"success": True, "data": {"clusters_created": 0, "message": "Not enough unclustered railway grievances"}, "error": None}

        embeddings = {}
        for g in grievances:
            gid = g.get("id")
            text = g.get("description", "")
            emb = await get_embedding(text)
            if emb is not None:
                embeddings[gid] = {"embedding": emb, "grievance": g}

        if len(embeddings) < 2:
            return {"success": True, "data": {"clusters_created": 0, "message": "Could not get enough embeddings"}, "error": None}

        ids = list(embeddings.keys())
        visited = set()
        clusters_created = 0

        for i, id_a in enumerate(ids):
            if id_a in visited:
                continue
            cluster_members = [id_a]
            visited.add(id_a)

            for j in range(i + 1, len(ids)):
                id_b = ids[j]
                if id_b in visited:
                    continue
                sim = cosine_similarity(embeddings[id_a]["embedding"], embeddings[id_b]["embedding"])
                if sim > 0.70:  # Slightly lower threshold for railway (fewer complaints per train)
                    g_a = embeddings[id_a]["grievance"]
                    g_b = embeddings[id_b]["grievance"]
                    if g_a.get("train_number") == g_b.get("train_number") or g_a.get("railway_zone") == g_b.get("railway_zone"):
                        cluster_members.append(id_b)
                        visited.add(id_b)

            if len(cluster_members) >= 2:
                first = embeddings[cluster_members[0]]["grievance"]
                category = first.get("category", "other")
                train_number = first.get("train_number", "Unknown")
                zone = first.get("railway_zone", "Unknown")
                summaries = [embeddings[m]["grievance"].get("ai_summary", "") or embeddings[m]["grievance"].get("description", "")[:50] for m in cluster_members]
                summary = f"{len(cluster_members)} {category} complaints for Train {train_number} ({zone}): " + "; ".join(summaries[:3])

                cluster_data = {
                    "category": category,
                    "train_number": train_number,
                    "railway_zone": zone,
                    "station": first.get("station"),
                    "member_ids": cluster_members,
                    "summary": summary[:500],
                    "count": len(cluster_members),
                }
                cluster_result = supabase.table("railway_clusters").insert(cluster_data).execute()
                if cluster_result.data:
                    cluster_id = cluster_result.data[0]["id"]
                    for mid in cluster_members:
                        supabase.table("railway_grievances").update({"cluster_id": cluster_id}).eq("id", mid).execute()
                    clusters_created += 1

        return {"success": True, "data": {"clusters_created": clusters_created}, "error": None}
    except Exception as e:
        logger.error("Railway cluster endpoint error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": True, "data": {"clusters_created": 0, "message": "Railway tables not created yet"}, "error": None}
        return {"success": False, "data": None, "error": str(e)}


# --- Dashboard ---

@router.get("/dashboard/stats")
async def get_railway_stats():
    from main import supabase
    if not supabase:
        return {"success": False, "data": {"total": 0, "open": 0, "resolved": 0, "critical": 0, "clusters_active": 0}, "error": "Database not configured"}
    try:
        all_result = supabase.table("railway_grievances").select("id, status, urgency").execute()
        grievances = all_result.data or []

        total = len(grievances)
        open_count = sum(1 for g in grievances if g.get("status") == "open")
        resolved = sum(1 for g in grievances if g.get("status") in ("resolved", "closed"))
        critical = sum(1 for g in grievances if (g.get("urgency") or 0) >= 4)

        clusters_result = supabase.table("railway_clusters").select("id").execute()
        clusters_active = len(clusters_result.data or [])

        return {
            "success": True,
            "data": {
                "total": total,
                "open": open_count,
                "resolved": resolved,
                "critical": critical,
                "clusters_active": clusters_active,
            },
            "error": None,
        }
    except Exception as e:
        logger.error("Railway dashboard stats error: %s", str(e))
        return {"success": True, "data": {"total": 0, "open": 0, "resolved": 0, "critical": 0, "clusters_active": 0}, "error": None}


@router.get("/dashboard/clusters")
async def get_railway_clusters():
    from main import supabase
    if not supabase:
        return {"success": False, "data": [], "error": "Database not configured"}
    try:
        result = supabase.table("railway_clusters").select("*").order("created_at", desc=True).execute()
        clusters = result.data or []

        for cluster in clusters:
            member_ids = cluster.get("member_ids") or []
            if member_ids:
                members_result = supabase.table("railway_grievances").select(
                    "id, passenger_name, description, ai_summary, urgency, status, train_number"
                ).in_("id", member_ids).execute()
                cluster["members"] = members_result.data or []
            else:
                cluster["members"] = []

        return {"success": True, "data": clusters, "error": None}
    except Exception as e:
        logger.error("Railway dashboard clusters error: %s", str(e))
        return {"success": True, "data": [], "error": None}


@router.get("/dashboard/trends")
async def get_railway_trends():
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        result = supabase.table("railway_grievances").select("category, status, urgency, railway_zone, train_number").execute()
        grievances = result.data or []

        cat_counts = {}
        for g in grievances:
            cat = g.get("category") or "other"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        by_category = [{"name": k, "count": v} for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])]

        status_counts = {}
        for g in grievances:
            s = g.get("status") or "open"
            status_counts[s] = status_counts.get(s, 0) + 1
        by_status = [{"name": k, "count": v} for k, v in status_counts.items()]

        zone_counts = {}
        for g in grievances:
            z = g.get("railway_zone") or "Unknown"
            zone_counts[z] = zone_counts.get(z, 0) + 1
        by_zone = [{"name": k, "count": v} for k, v in sorted(zone_counts.items(), key=lambda x: -x[1])]

        return {
            "success": True,
            "data": {"by_category": by_category, "by_status": by_status, "by_zone": by_zone},
            "error": None,
        }
    except Exception as e:
        logger.error("Railway dashboard trends error: %s", str(e))
        return {"success": True, "data": {"by_category": [], "by_status": [], "by_zone": []}, "error": None}


@router.get("/dashboard/brief")
async def get_railway_brief():
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        clusters_result = supabase.table("railway_clusters").select("*").execute()
        clusters = clusters_result.data or []

        if not clusters:
            return {
                "success": True,
                "data": {"brief": "No active railway clusters. Brief will be generated when complaint patterns are detected."},
                "error": None,
            }

        clusters_data = []
        for c in clusters:
            clusters_data.append({
                "category": c.get("category"),
                "train_number": c.get("train_number"),
                "railway_zone": c.get("railway_zone"),
                "count": c.get("count"),
                "summary": c.get("summary"),
            })

        brief = await generate_brief(clusters_data)
        return {"success": True, "data": {"brief": brief}, "error": None}
    except Exception as e:
        logger.error("Railway dashboard brief error: %s", str(e))
        return {"success": True, "data": {"brief": "Railway module is ready. Tables will be set up on first use."}, "error": None}


@router.get("/zones")
async def get_railway_zones():
    return {"success": True, "data": {"zones": RAILWAY_ZONES, "categories": RAILWAY_CATEGORIES}, "error": None}
