import logging
from fastapi import APIRouter
from typing import Optional
from utils.db_helpers import is_table_missing

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.get("")
async def get_predictions(ward: Optional[str] = None, category: Optional[str] = None):
    """Get latest predictions, optionally filtered by ward or category."""
    from main import supabase
    if not supabase:
        return {"success": False, "data": [], "error": "Database not configured"}
    try:
        query = supabase.table("predictions").select("*").order("generated_at", desc=True)
        if ward:
            query = query.eq("ward", ward)
        if category:
            query = query.eq("category", category)
        result = query.limit(100).execute()
        return {"success": True, "data": result.data or [], "error": None}
    except Exception as e:
        logger.error("Get predictions error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": True, "data": [], "error": None}
        return {"success": False, "data": [], "error": str(e)}


@router.post("/run")
async def run_predictions():
    """Manually trigger prediction generation."""
    try:
        from jobs.scheduler import generate_predictions
        result = generate_predictions()
        return {"success": True, "data": result, "error": None}
    except Exception as e:
        logger.error("Run predictions error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": True, "data": {"predictions_generated": 0, "message": "Predictions table not created yet."}, "error": None}
        return {"success": False, "data": None, "error": str(e)}
