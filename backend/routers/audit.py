import logging
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from utils.db_helpers import is_table_missing

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/audit", tags=["Audit"])


class BudgetCreate(BaseModel):
    grievance_id: Optional[str] = None
    cluster_id: Optional[str] = None
    department: str
    amount_allocated: float
    amount_spent: float = 0
    description: Optional[str] = None


@router.post("/budget")
async def create_budget_entry(req: BudgetCreate):
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        entry_data = {
            "grievance_id": req.grievance_id,
            "cluster_id": req.cluster_id,
            "department": req.department,
            "amount_allocated": req.amount_allocated,
            "amount_spent": req.amount_spent,
            "description": req.description,
        }
        result = supabase.table("budget_allocations").insert(entry_data).execute()
        if not result.data:
            return {"success": False, "data": None, "error": "Failed to create budget entry"}
        return {"success": True, "data": result.data[0], "error": None}
    except Exception as e:
        logger.error("Create budget entry error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": False, "data": None, "error": "Budget tables not created yet. Run V2 schema SQL in Supabase SQL Editor."}
        return {"success": False, "data": None, "error": str(e)}


@router.get("/budget")
async def get_budget_entries(
    department: Optional[str] = None,
    flagged: Optional[bool] = None,
    limit: int = 50,
):
    from main import supabase
    if not supabase:
        return {"success": False, "data": [], "error": "Database not configured"}
    try:
        query = supabase.table("budget_allocations").select("*")
        if department:
            query = query.eq("department", department)
        if flagged is not None:
            query = query.eq("auditor_flagged", flagged)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return {"success": True, "data": result.data or [], "error": None}
    except Exception as e:
        logger.error("Get budget entries error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": True, "data": [], "error": None}
        return {"success": False, "data": [], "error": str(e)}


@router.get("/budget/stats")
async def get_budget_stats():
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        result = supabase.table("budget_allocations").select("*").execute()
        entries = result.data or []

        total_allocated = sum(float(e.get("amount_allocated") or 0) for e in entries)
        total_spent = sum(float(e.get("amount_spent") or 0) for e in entries)
        total_flagged = sum(1 for e in entries if e.get("auditor_flagged"))
        flagged_amount = sum(float(e.get("amount_allocated") or 0) for e in entries if e.get("auditor_flagged"))

        # By department breakdown
        dept_data = {}
        for e in entries:
            dept = e.get("department", "Unknown")
            if dept not in dept_data:
                dept_data[dept] = {"allocated": 0, "spent": 0, "flagged": 0}
            dept_data[dept]["allocated"] += float(e.get("amount_allocated") or 0)
            dept_data[dept]["spent"] += float(e.get("amount_spent") or 0)
            if e.get("auditor_flagged"):
                dept_data[dept]["flagged"] += 1
        by_department = [{"name": k, **v} for k, v in sorted(dept_data.items(), key=lambda x: -x[1]["allocated"])]

        return {
            "success": True,
            "data": {
                "total_allocated": total_allocated,
                "total_spent": total_spent,
                "total_entries": len(entries),
                "total_flagged": total_flagged,
                "flagged_amount": flagged_amount,
                "by_department": by_department,
            },
            "error": None,
        }
    except Exception as e:
        logger.error("Budget stats error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": True, "data": {"total_allocated": 0, "total_spent": 0, "total_entries": 0, "total_flagged": 0, "flagged_amount": 0, "by_department": []}, "error": None}
        return {"success": False, "data": None, "error": str(e)}


@router.get("/flagged")
async def get_flagged_entries():
    from main import supabase
    if not supabase:
        return {"success": False, "data": [], "error": "Database not configured"}
    try:
        result = supabase.table("budget_allocations").select("*").eq("auditor_flagged", True).order("flagged_at", desc=True).execute()
        return {"success": True, "data": result.data or [], "error": None}
    except Exception as e:
        logger.error("Get flagged entries error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": True, "data": [], "error": None}
        return {"success": False, "data": [], "error": str(e)}


@router.patch("/budget/{budget_id}/flag")
async def flag_budget_entry(budget_id: str, reason: str = "Manual audit flag"):
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("budget_allocations").update({
            "auditor_flagged": True,
            "flag_reason": reason,
            "flagged_at": now,
        }).eq("id", budget_id).execute()
        return {"success": True, "data": {"message": "Budget entry flagged for audit"}, "error": None}
    except Exception as e:
        logger.error("Flag budget entry error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": False, "data": None, "error": "Budget tables not created yet."}
        return {"success": False, "data": None, "error": str(e)}


@router.patch("/budget/{budget_id}/spend")
async def update_budget_spent(budget_id: str, amount_spent: float = 0):
    from main import supabase
    if not supabase:
        return {"success": False, "data": None, "error": "Database not configured"}
    try:
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("budget_allocations").update({
            "amount_spent": amount_spent,
            "updated_at": now,
        }).eq("id", budget_id).execute()
        return {"success": True, "data": {"message": "Budget spending updated"}, "error": None}
    except Exception as e:
        logger.error("Update budget spent error: %s", str(e))
        if is_table_missing(str(e)):
            return {"success": False, "data": None, "error": "Budget tables not created yet."}
        return {"success": False, "data": None, "error": str(e)}
