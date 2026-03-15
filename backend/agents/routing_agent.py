"""
Intelligent Routing Agent
Autonomously assigns grievances to optimal officers using multi-factor analysis
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime
from .base_agent import BaseAgent, ActionType

logger = logging.getLogger(__name__)


class RoutingAgent(BaseAgent):
    """
    Multi-factor intelligent routing agent:
    1. Analyzes grievance characteristics
    2. Evaluates officer expertise and capacity
    3. Considers workload balance and patterns
    4. Predicts success probability
    5. Makes optimal assignment
    
    Factors considered:
    - Officer expertise match
    - Current workload
    - Resolution success history
    - Geographic proximity
    - Time availability
    - Similar case track record
    """
    
    def __init__(self):
        super().__init__(
            name="RoutingAgent",
            role="Optimal Resource Allocator",
            model_name="llama-3.1-8b"
        )
    
    async def act(self, action_type: ActionType, action_data: Dict) -> Dict:
        """Route-specific actions"""
        
        if action_type == ActionType.RETRIEVE_DATA:
            return await self._fetch_officer_data(action_data)
        
        elif action_type == ActionType.ANALYZE:
            return await self._calculate_fit_scores(action_data)
        
        elif action_type == ActionType.MAKE_DECISION:
            return await self._compute_optimal_assignment(action_data)
        
        return {"status": "unknown_action"}
    
    async def _fetch_officer_data(self, data: Dict) -> Dict:
        """Retrieve all officer metrics from database"""
        from main import supabase
        
        if not supabase:
            return {"officers": [], "ready": False}
        
        try:
            # Get all officers
            officers_result = supabase.table("officers").select("*").execute()
            officers = officers_result.data or []
            
            # Enrich with stats
            enriched = []
            for officer in officers:
                officer_id = officer.get("id")
                
                # Get their assignments
                assignments = supabase.table("assignments").select("*").eq(
                    "assigned_officer_id", officer_id
                ).execute()
                assignments = assignments.data or []
                
                # Calculate stats
                open_count = len([a for a in assignments if a.get("status") == "open"])
                resolved_count = len([a for a in assignments if a.get("status") == "resolved"])
                
                enriched.append({
                    "id": officer_id,
                    "email": officer.get("email"),
                    "name": officer.get("name", "Officer"),
                    "expertise_categories": officer.get("expertise_categories", []),
                    "ward": officer.get("ward"),
                    "current_open_count": open_count,
                    "resolution_rate": resolved_count / max(len(assignments), 1),
                    "avg_resolution_time_hours": officer.get("avg_resolution_time_hours", 72),
                    "citizen_satisfaction": officer.get("citizen_satisfaction", 3.5),
                    "specializations": officer.get("specializations", [])
                })
            
            self.thought_log.add_observation("officers_fetched", len(enriched))
            
            return {
                "officers": enriched,
                "ready": True
            }
        
        except Exception as e:
            logger.error(f"Failed to fetch officer data: {e}")
            return {"officers": [], "ready": False}
    
    async def _calculate_fit_scores(self, data: Dict) -> Dict:
        """Calculate fit score for each officer given grievance"""
        from utils.groq_client import call_groq
        
        grievance = data.get("grievance", {})
        officers = data.get("officers", [])
        
        if not officers:
            return {"fit_scores": [], "analysis": "No officers available"}
        
        # Use Groq to calculate intelligent fit scores
        officers_str = json.dumps(officers, indent=2)
        grievance_str = json.dumps({
            "category": grievance.get("category"),
            "urgency": grievance.get("urgency"),
            "ward": grievance.get("ward"),
            "credibility": grievance.get("credibility_score", 50)
        }, indent=2)
        
        scoring_prompt = f"""
Match this grievance to the best officers:

GRIEVANCE:
{grievance_str}

AVAILABLE OFFICERS:
{officers_str}

For EACH officer, calculate:
1. Expertise Match (0-100): Does their expertise fit?
2. Capacity Score (0-100): Can they handle more work?
3. Success Probability (0-100): Likelihood they'll resolve well?
4. Workload Balance (0-100): Fair distribution?
5. Track Record (0-100): Have they solved similar cases?

Return JSON array:
[{{
  "officer_id": "id",
  "expertise_match": <0-100>,
  "capacity_score": <0-100>,
  "success_probability": <0-100>,
  "workload_balance": <0-100>,
  "track_record": <0-100>,
  "overall_fit": <0-100>,
  "reasoning": "why this officer is/isn't suitable"
}}]
"""
        response = await call_groq(scoring_prompt)
        
        try:
            fit_scores = json.loads(response)
            self.thought_log.add_observation("fit_scores_calculated", len(fit_scores))
            
            # Sort by overall_fit
            fit_scores = sorted(fit_scores, key=lambda x: x.get("overall_fit", 0), reverse=True)
            
            return {
                "fit_scores": fit_scores,
                "top_candidates": [f["officer_id"] for f in fit_scores[:3]],
                "ready": True
            }
        except Exception as e:
            logger.error(f"Fit score calculation failed: {e}")
            return {"fit_scores": [], "ready": False}
    
    async def _compute_optimal_assignment(self, data: Dict) -> Dict:
        """Make final assignment decision with multi-factor analysis"""
        fit_scores = data.get("fit_scores", [])
        officers_dict = {o["id"]: o for o in data.get("officers", [])}
        
        if not fit_scores:
            return {"decision": "no_suitable_officer", "reasoning": "No officers available"}
        
        # Select top officer
        top_officer_id = fit_scores[0]["officer_id"]
        top_officer = officers_dict.get(top_officer_id)
        top_fit = fit_scores[0]
        
        if not top_officer:
            return {"decision": "assignment_failed", "reasoning": "Officer metadata missing"}
        
        # Generate reasoning for this assignment
        from utils.groq_client import call_groq
        
        reasoning_prompt = f"""
Explain why this is the optimal assignment:

Officer: {json.dumps(top_officer)}
Fit Scores: {json.dumps(top_fit)}

Provide:
1. Why this officer? (primary reason)
2. What's their competitive advantage?
3. Any risks to mention?
4. Alternative officers if this fails?

Keep it concise for officer communication.
"""
        
        reasoning_text = await call_groq(reasoning_prompt)
        
        return {
            "assigned_officer_id": top_officer_id,
            "assigned_officer_email": top_officer.get("email"),
            "assigned_officer_name": top_officer.get("name"),
            "fit_score": top_fit.get("overall_fit", 0),
            "confidence": min(top_fit.get("success_probability", 50) / 100.0, 1.0),
            "reasoning": reasoning_text,
            "alternatives": [
                {
                    "officer_id": fs["officer_id"],
                    "fit_score": fs["overall_fit"]
                }
                for fs in fit_scores[1:3]
            ]
        }
    
    async def route_grievance(self, grievance_data: Dict, all_officers: List[Dict] = None) -> Dict:
        """
        Main entry point: Intelligently route grievance to optimal officer
        
        Input:
        {
            "id": "grievance_id",
            "category": "water",
            "urgency": 4,
            "ward": "Ward 5",
            "credibility_score": 75
        }
        
        Output:
        {
            "grievance_id": "id",
            "assigned_officer_id": "officer_id",
            "assigned_officer_email": "officer@email.com",
            "fit_score": 92,
            "confidence": 0.88,
            "reasoning": "why this assignment",
            "alternatives": [...]
        }
        """
        
        problem = f"""
Intelligently route this grievance to the optimal officer:
- Category: {grievance_data.get('category', 'other')}
- Urgency: {grievance_data.get('urgency', 3)}/5
- Ward: {grievance_data.get('ward', 'Unknown')}
- Credibility: {grievance_data.get('credibility_score', 50)}/100

Consider: expertise match, workload balance, success probability, geographic factors.
Make the BEST assignment.
"""
        
        context = {
            "grievance": grievance_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Run agent loop with custom actions
        # THINK phase
        approaches = await self.think(problem, context)
        self.thought_log.add_thought(f"Routing approaches: {approaches}")
        
        # ACT phase - fetch officer data
        officer_data = await self.act(ActionType.RETRIEVE_DATA, {"ward": grievance_data.get("ward")})
        
        # ACT phase - calculate fit scores
        fit_result = await self.act(
            ActionType.ANALYZE,
            {
                "grievance": grievance_data,
                "officers": officer_data.get("officers", [])
            }
        )
        
        # DECIDE phase - make assignment
        assignment = await self.act(
            ActionType.MAKE_DECISION,
            {
                "fit_scores": fit_result.get("fit_scores", []),
                "officers": officer_data.get("officers", [])
            }
        )
        
        return {
            "success": True,
            "agent": "RoutingAgent",
            "grievance_id": grievance_data.get("id"),
            "result": assignment,
            "reasoning_trace": self.thought_log.to_dict(),
            "iterations": self.iteration
        }
