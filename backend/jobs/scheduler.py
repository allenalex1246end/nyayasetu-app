import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


async def run_cluster_detection():
    """Run cluster detection on unclustered grievances."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("http://localhost:8000/api/cluster")
            if response.status_code == 200:
                data = response.json()
                created = data.get("data", {}).get("clusters_created", 0)
                if created > 0:
                    logger.info("Cluster detection: %d clusters created", created)
            else:
                logger.error("Cluster detection failed: %s", response.status_code)
    except Exception as e:
        logger.error("Cluster detection job error: %s", str(e))


async def run_railway_cluster_detection():
    """Run cluster detection on unclustered railway grievances."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("http://localhost:8000/api/railway/cluster")
            if response.status_code == 200:
                data = response.json()
                created = data.get("data", {}).get("clusters_created", 0)
                if created > 0:
                    logger.info("Railway cluster detection: %d clusters created", created)
            else:
                logger.error("Railway cluster detection failed: %s", response.status_code)
    except Exception as e:
        logger.error("Railway cluster detection job error: %s", str(e))


def check_sla_breaches():
    """Find grievances open > 48hrs and mark as breached."""
    try:
        from main import supabase
        threshold = datetime.now(timezone.utc) - timedelta(hours=48)
        threshold_str = threshold.isoformat()

        result = supabase.table("grievances").select("id, created_at").eq("status", "open").lt("created_at", threshold_str).execute()
        grievances = result.data or []

        for g in grievances:
            gid = g.get("id")
            try:
                supabase.table("grievances").update({"status": "breached"}).eq("id", gid).execute()
                supabase.table("actions").insert({
                    "grievance_id": gid,
                    "action_type": "breach_detected",
                    "performed_by": "system",
                    "notes": "SLA breach: complaint open for more than 48 hours",
                }).execute()
                logger.info("SLA breach detected for grievance %s", gid)
            except Exception as inner_e:
                logger.error("Failed to mark breach for %s: %s", gid, str(inner_e))

    except Exception as e:
        logger.error("SLA breach check job error: %s", str(e))


def check_fake_closures():
    """Find resolved grievances where citizen hasn't confirmed within 2 minutes. Auto-reopen.
    Also flags any associated budget allocations for audit (FinTech embezzlement detection)."""
    try:
        from main import supabase
        # 2-minute timeout for demo (would be 48hrs in production)
        threshold = datetime.now(timezone.utc) - timedelta(minutes=2)
        threshold_str = threshold.isoformat()

        result = (
            supabase.table("grievances")
            .select("id, resolved_at, citizen_name")
            .eq("status", "resolved")
            .eq("resolution_confirmed", False)
            .lt("resolved_at", threshold_str)
            .execute()
        )
        grievances = result.data or []

        for g in grievances:
            gid = g.get("id")
            try:
                supabase.table("grievances").update({
                    "status": "reopened",
                    "resolved_at": None,
                }).eq("id", gid).execute()
                supabase.table("actions").insert({
                    "grievance_id": gid,
                    "action_type": "reopened",
                    "performed_by": "system",
                    "notes": "Auto-reopened: citizen did not confirm resolution within 2 minutes",
                }).execute()
                logger.info("Fake closure detected, reopened grievance %s", gid)

                # FinTech Audit: Flag any budget allocations tied to this grievance
                try:
                    budget_result = supabase.table("budget_allocations").select("id").eq("grievance_id", gid).eq("auditor_flagged", False).execute()
                    for b in (budget_result.data or []):
                        supabase.table("budget_allocations").update({
                            "auditor_flagged": True,
                            "flag_reason": "Auto-flagged: fake closure detected, funds may be misallocated",
                            "flagged_at": datetime.now(timezone.utc).isoformat(),
                        }).eq("id", b["id"]).execute()
                        logger.info("Budget entry %s flagged due to fake closure of grievance %s", b["id"], gid)
                except Exception as budget_err:
                    logger.error("Failed to flag budget for %s: %s", gid, str(budget_err))

            except Exception as inner_e:
                logger.error("Failed to reopen %s: %s", gid, str(inner_e))

    except Exception as e:
        logger.error("Fake closure check job error: %s", str(e))


def generate_predictions():
    """Aggregate historical grievance counts by ward+category+month, run time-series forecast.
    Uses simple exponential smoothing (numpy only, no heavy deps)."""
    try:
        from main import supabase

        # 1. Fetch all grievances with timestamps
        result = supabase.table("grievances").select("ward, category, created_at").execute()
        grievances = result.data or []

        if not grievances:
            return {"predictions_generated": 0, "message": "No historical data"}

        # 2. Aggregate: count per (ward, category, YYYY-MM)
        counts = defaultdict(lambda: defaultdict(int))
        for g in grievances:
            ward = g.get("ward", "Unknown")
            cat = g.get("category", "other")
            created = g.get("created_at", "")
            month = created[:7] if created else ""  # YYYY-MM
            if month:
                counts[(ward, cat)][month] += 1

        # 3. Simple exponential smoothing for each series with >= 3 months
        def exp_smooth(values, alpha=0.6):
            result_val = values[0]
            for v in values[1:]:
                result_val = alpha * v + (1 - alpha) * result_val
            return result_val

        predictions = []
        for (ward, cat), monthly in counts.items():
            sorted_months = sorted(monthly.keys())
            if len(sorted_months) < 3:
                continue
            values = [monthly[m] for m in sorted_months]

            try:
                forecast = exp_smooth(values)
                predicted = max(0, int(round(forecast)))

                # Determine trend
                if len(values) >= 2:
                    if values[-1] > values[-2]:
                        trend = "rising"
                    elif values[-1] < values[-2]:
                        trend = "falling"
                    else:
                        trend = "stable"
                else:
                    trend = "stable"

                # Confidence based on data volume
                confidence = min(0.95, 0.5 + len(values) * 0.05)

                # Next month calculation
                last_month_str = sorted_months[-1]
                year, month_num = int(last_month_str[:4]), int(last_month_str[5:7])
                if month_num == 12:
                    next_month = f"{year + 1}-01"
                else:
                    next_month = f"{year}-{month_num + 1:02d}"

                predictions.append({
                    "ward": ward,
                    "category": cat,
                    "month": next_month,
                    "predicted_count": predicted,
                    "confidence": round(confidence, 2),
                    "trend": trend,
                })
            except Exception:
                continue

        # 4. Clear old predictions, insert new
        try:
            supabase.table("predictions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        except Exception:
            pass  # Table may be empty

        if predictions:
            supabase.table("predictions").insert(predictions).execute()

        logger.info("Generated %d predictions", len(predictions))
        return {"predictions_generated": len(predictions)}

    except Exception as e:
        logger.error("Prediction generation error: %s", str(e))
        return {"predictions_generated": 0, "error": str(e)}
