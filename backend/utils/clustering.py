"""
Clustering utilities: group similar grievances using embeddings and semantic similarity.
"""
import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Clustering thresholds
SIMILARITY_THRESHOLD = 0.75
SAME_WARD_WEIGHT = 1.2  # Boost similarity if same ward
SAME_CATEGORY_WEIGHT = 1.1  # Boost similarity if same category


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)


def compute_adjusted_similarity(
    desc1: str,
    desc2: str,
    embedding1: List[float],
    embedding2: List[float],
    ward1: str,
    ward2: str,
    category1: str,
    category2: str,
) -> float:
    """
    Compute similarity with adjustments for ward/category matching.
    Returns value between 0 and 1.
    """
    base_similarity = cosine_similarity(embedding1, embedding2)
    
    # Apply boosts for matching context
    boost = 1.0
    if ward1 and ward2 and ward1 == ward2:
        boost *= SAME_WARD_WEIGHT
    if category1 and category2 and category1.lower() == category2.lower():
        boost *= SAME_CATEGORY_WEIGHT
    
    adjusted = min(1.0, base_similarity * boost)
    return adjusted


def should_cluster(
    similarity: float,
    ward_match: bool,
    category_match: bool,
) -> bool:
    """
    Determine if two grievances should be clustered.
    
    Rule: Similarity >= threshold AND (same ward OR same category)
    """
    meets_similarity = similarity >= SIMILARITY_THRESHOLD
    meets_context = ward_match or category_match
    
    return meets_similarity and meets_context


async def get_embedding_from_gemini(
    text: str,
    gemini_client: Any,
) -> Optional[List[float]]:
    """Get embedding from Google Gemini API."""
    try:
        result = await gemini_client.embed_text(text)
        return result.get("embedding") if result else None
    except Exception as e:
        logger.error("Embedding error: %s", str(e))
        return None


async def get_embeddings_batch(
    descriptions: List[str],
    gemini_client: Any,
) -> Dict[str, List[float]]:
    """
    Get embeddings for a batch of descriptions.
    Returns dict: {description[:50]: embedding}
    """
    embeddings = {}
    
    for desc in descriptions:
        if not desc or len(desc) < 5:
            continue
        
        embedding = await get_embedding_from_gemini(desc, gemini_client)
        if embedding:
            key = desc[:50]  # Use first 50 chars as key
            embeddings[key] = embedding
    
    return embeddings


class ClusterBuilder:
    """Helper class to build clusters from grievances."""
    
    def __init__(self):
        self.clusters: Dict[str, Dict[str, Any]] = {}
        self.grievance_to_cluster: Dict[str, str] = {}
        self.cluster_counter = 0
    
    def add_grievance_to_cluster(
        self,
        grievance_id: str,
        cluster_id: str,
        grievance_data: Dict[str, Any],
    ):
        """Add grievance to an existing or new cluster."""
        if cluster_id not in self.clusters:
            self.clusters[cluster_id] = {
                "id": cluster_id,
                "member_ids": [],
                "grievances": [],
                "category": grievance_data.get("category"),
                "ward": grievance_data.get("ward"),
                "summaries": [],
                "urgencies": [],
            }
        
        cluster = self.clusters[cluster_id]
        if grievance_id not in cluster["member_ids"]:
            cluster["member_ids"].append(grievance_id)
            cluster["grievances"].append(grievance_data)
            cluster["summaries"].append(grievance_data.get("ai_summary", ""))
            urgency = grievance_data.get("urgency", 3)
            if urgency:
                cluster["urgencies"].append(urgency)
        
        self.grievance_to_cluster[grievance_id] = cluster_id
    
    def merge_clusters(self, cluster_id1: str, cluster_id2: str):
        """Merge two clusters into one."""
        if cluster_id1 not in self.clusters or cluster_id2 not in self.clusters:
            return
        
        c1 = self.clusters[cluster_id1]
        c2 = self.clusters[cluster_id2]
        
        # Add all from c2 to c1
        c1["member_ids"].extend(c2["member_ids"])
        c1["grievances"].extend(c2["grievances"])
        c1["summaries"].extend(c2["summaries"])
        c1["urgencies"].extend(c2["urgencies"])
        
        # Update mapping
        for gid in c2["member_ids"]:
            self.grievance_to_cluster[gid] = cluster_id1
        
        # Remove c2
        del self.clusters[cluster_id2]
    
    def get_new_cluster_id(self) -> str:
        """Generate new unique cluster ID."""
        self.cluster_counter += 1
        return f"cluster_{self.cluster_counter}"
    
    def get_clusters(self) -> List[Dict[str, Any]]:
        """Get all clusters as list."""
        return list(self.clusters.values())


async def cluster_grievances(
    grievances: List[Dict[str, Any]],
    gemini_client: Any,
    supabase_client: Any,
    table_name: str = "grievances",
    cluster_table: str = "clusters",
) -> Tuple[int, int]:
    """
    Cluster grievances using embeddings and semantic similarity.
    
    Returns: (clusters_created, grievances_clustered)
    """
    if not grievances or len(grievances) < 2:
        return 0, 0
    
    logger.info(f"Starting clustering for {len(grievances)} grievances from {table_name}")
    
    builder = ClusterBuilder()
    
    # Step 1: Get embeddings for all descriptions
    descriptions = [g.get("description", "") for g in grievances if g.get("description")]
    embeddings_map = await get_embeddings_batch(descriptions, gemini_client)
    
    if not embeddings_map:
        logger.warning("No embeddings generated")
        return 0, 0
    
    # Step 2: Compare each grievance with others and cluster
    for i, g1 in enumerate(grievances):
        g1_id = g1.get("id")
        if g1_id in builder.grievance_to_cluster:
            continue  # Already clustered
        
        # Get embedding for this grievance
        desc1_key = g1.get("description", "")[:50]
        embedding1 = embeddings_map.get(desc1_key)
        
        if not embedding1:
            continue
        
        # Create new cluster for this grievance
        cluster_id = builder.get_new_cluster_id()
        builder.add_grievance_to_cluster(g1_id, cluster_id, g1)
        
        # Find similar grievances
        for j, g2 in enumerate(grievances):
            if j <= i:
                continue  # Already compared
            
            g2_id = g2.get("id")
            if g2_id in builder.grievance_to_cluster:
                continue  # Already in a cluster
            
            desc2_key = g2.get("description", "")[:50]
            embedding2 = embeddings_map.get(desc2_key)
            
            if not embedding2:
                continue
            
            # Compute similarity
            similarity = compute_adjusted_similarity(
                g1.get("description", ""),
                g2.get("description", ""),
                embedding1,
                embedding2,
                g1.get("ward"),
                g2.get("ward"),
                g1.get("category"),
                g2.get("category"),
            )
            
            # Check if should cluster
            ward_match = g1.get("ward") == g2.get("ward")
            category_match = (g1.get("category", "").lower() == 
                            g2.get("category", "").lower())
            
            if should_cluster(similarity, ward_match, category_match):
                builder.add_grievance_to_cluster(g2_id, cluster_id, g2)
                logger.debug(f"Clustered {g2_id} with {g1_id} (similarity: {similarity:.2f})")
    
    # Step 3: Filter out single-grievance clusters and save multi-grievance ones
    clusters_to_save = [c for c in builder.get_clusters() if len(c["member_ids"]) > 1]
    
    clusters_created = 0
    grievances_clustered = 0
    
    for cluster in clusters_to_save:
        try:
            # Generate cluster summary from Groq
            brief = await generate_cluster_brief(cluster, gemini_client)
            
            # Save cluster to DB
            cluster_data = {
                "category": cluster.get("category"),
                "ward": cluster.get("ward"),
                "member_ids": cluster["member_ids"],
                "summary": " | ".join(cluster["summaries"][:3]),  # First 3 summaries
                "ai_brief": brief,
                "count": len(cluster["member_ids"]),
                "alert_sent": False,
            }
            
            result = supabase_client.table(cluster_table).insert(cluster_data).execute()
            
            if result.data:
                saved_cluster = result.data[0]
                cluster_db_id = saved_cluster.get("id")
                
                # Update grievances with cluster_id
                for gid in cluster["member_ids"]:
                    supabase_client.table(table_name).update(
                        {"cluster_id": cluster_db_id}
                    ).eq("id", gid).execute()
                
                clusters_created += 1
                grievances_clustered += len(cluster["member_ids"])
                
                logger.info(f"Created cluster: {cluster_db_id} with {len(cluster['member_ids'])} grievances")
        
        except Exception as e:
            logger.error(f"Failed to save cluster: {str(e)}")
            continue
    
    logger.info(f"Clustering complete: {clusters_created} clusters created, {grievances_clustered} grievances clustered")
    
    return clusters_created, grievances_clustered


async def generate_cluster_brief(
    cluster: Dict[str, Any],
    groq_client: Any,
) -> str:
    """Generate AI brief summarizing the cluster."""
    try:
        summaries = cluster.get("summaries", [])[:5]  # First 5 summaries
        combined = " ".join(summaries)
        
        prompt = f"""
You are an AI assistant helping government grievance analysis.

Summarize these related grievances into a brief intelligence report (2-3 sentences):
{combined}

Focus on:
1. Common theme
2. Affected area/people
3. Urgency level

Brief report:
"""
        
        brief = await groq_client.predict(prompt)
        return brief if brief else " | ".join(summaries[:2])
    
    except Exception as e:
        logger.error(f"Brief generation error: {str(e)}")
        return ""
