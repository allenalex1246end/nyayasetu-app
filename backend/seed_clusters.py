"""
seed_clusters.py — Create sample clusters from existing grievances
Run: py seed_clusters.py (from backend/ directory)

This script:
1. Fetches grievances with same ward & category
2. Groups them into clusters
3. Updates grievances with cluster_id
4. Inserts cluster records
"""

import os
import sys
import uuid
import asyncio
from datetime import datetime, timezone
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Set SUPABASE_URL and SUPABASE_KEY in .env first.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✓ Connected to Supabase")


def create_clusters():
    """Create clusters from existing grievances."""
    
    # Fetch all grievances
    result = supabase.table("grievances").select("id, ward, category, description, ai_summary, urgency").execute()
    grievances = result.data or []
    
    print(f"\n📊 Found {len(grievances)} grievances")
    
    # Group by ward + category
    groups = defaultdict(list)
    for g in grievances:
        key = (g.get("ward"), g.get("category"))
        groups[key].append(g)
    
    print(f"📍 Found {len(groups)} ward+category combinations")
    
    clusters_created = 0
    grievances_updated = 0
    
    # Create clusters for groups with 2+ grievances
    for (ward, category), group_grievances in groups.items():
        if len(group_grievances) < 2:
            continue  # Skip single grievances
        
        cluster_id = str(uuid.uuid4())
        
        # Get member IDs
        member_ids = [g["id"] for g in group_grievances]
        
        # Calculate avg urgency
        avg_urgency = sum(g.get("urgency", 3) for g in group_grievances) / len(group_grievances)
        
        # Get first summary
        first_summary = group_grievances[0].get("ai_summary") or group_grievances[0].get("description", "")[:100]
        
        # Create cluster record
        cluster_data = {
            "id": cluster_id,
            "member_ids": [str(gid) for gid in member_ids],
            "category": category,
            "ward": ward,
            "summary": first_summary,
            "count": len(member_ids),
            "ai_brief": f"{len(member_ids)} similar issues in {ward} ({category}). Requires coordinated response.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            supabase.table("clusters").insert(cluster_data).execute()
            print(f"✓ Cluster created: {category} in {ward} ({len(member_ids)} grievances)")
            clusters_created += 1
            
            # Update grievances with cluster_id
            for gid in member_ids:
                supabase.table("grievances").update({"cluster_id": cluster_id}).eq("id", gid).execute()
            grievances_updated += len(member_ids)
            
        except Exception as e:
            print(f"✗ Error creating cluster: {str(e)[:100]}")
    
    print(f"\n✅ Summary:")
    print(f"   Clusters created: {clusters_created}")
    print(f"   Grievances linked: {grievances_updated}")


if __name__ == "__main__":
    try:
        create_clusters()
        print("\n✓ Clustering complete!")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
