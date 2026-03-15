"""
Policy Recommendation Agent
Generates governance insights, identifies systemic issues, and creates actionable briefs
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from .base_agent import BaseAgent, ActionType

logger = logging.getLogger(__name__)


class PolicyAgent(BaseAgent):
    """
    Autonomous governance intelligence agent:
    1. Analyzes grievance patterns and trends
    2. Identifies systemic policy failures
    3. Detects emerging issues
    4. Generates governance briefs for officers
    5. Proposes targeted interventions
    
    Outputs:
    - Critical pattern alerts
    - Policy failure analysis
    - Resource recommendations
    - Preventive action plans
    """
    
    def __init__(self):
        super().__init__(
            name="PolicyAgent",
            role="Governance Intelligence Officer",
            model_name="llama-3.1-8b"
        )
    
    async def act(self, action_type: ActionType, action_data: Dict) -> Dict:
        """Policy-specific actions"""
        
        if action_type == ActionType.RETRIEVE_DATA:
            return await self._fetch_grievance_patterns(action_data)
        
        elif action_type == ActionType.ANALYZE:
            return await self._analyze_systemic_issues(action_data)
        
        elif action_type == ActionType.GENERATE_INSIGHT:
            return await self._generate_policy_brief(action_data)
        
        return {"status": "unknown_action"}
    
    async def _fetch_grievance_patterns(self, data: Dict) -> Dict:
        """Fetch and aggregate grievance patterns from database"""
        from main import supabase
        
        if not supabase:
            return {"patterns": {}, "ready": False}
        
        try:
            days_back = data.get("days", 30)
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            # Get all recent grievances
            grievances_result = supabase.table("grievances").select("*").gte(
                "created_at", cutoff_date
            ).execute()
            grievances = grievances_result.data or []
            
            # Analyze patterns
            patterns = {
                "total_grievances": len(grievances),
                "by_category": {},
                "by_ward": {},
                "by_urgency": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                "by_status": {},
                "unresolved_sla": 0,
                "resolution_rate": 0
            }
            
            for g in grievances:
                # By category
                cat = g.get("category", "other")
                patterns["by_category"][cat] = patterns["by_category"].get(cat, 0) + 1
                
                # By ward
                ward = g.get("ward", "Unknown")
                patterns["by_ward"][ward] = patterns["by_ward"].get(ward, 0) + 1
                
                # By urgency
                urgency = min(5, max(1, g.get("urgency", 3)))
                patterns["by_urgency"][urgency] += 1
                
                # By status
                status = g.get("status", "open")
                patterns["by_status"][status] = patterns["by_status"].get(status, 0) + 1
                
                # SLA check (> 72 hours)
                if status == "open" and g.get("created_at"):
                    created = datetime.fromisoformat(g.get("created_at").replace("Z", "+00:00"))
                    hours_open = (datetime.now(created.tzinfo) - created).total_seconds() / 3600
                    if hours_open > 72:
                        patterns["unresolved_sla"] += 1
            
            resolved = patterns["by_status"].get("resolved", 0)
            patterns["resolution_rate"] = resolved / max(len(grievances), 1)
            
            self.thought_log.add_observation("patterns_fetched", patterns)
            
            return {
                "patterns": patterns,
                "grievance_sample": grievances[:5],
                "ready": True
            }
        
        except Exception as e:
            logger.error(f"Pattern fetching failed: {e}")
            return {"patterns": {}, "ready": False}
    
    async def _analyze_systemic_issues(self, data: Dict) -> Dict:
        """Analyze patterns for systemic governance issues"""
        from utils.groq_client import call_groq
        
        patterns = data.get("patterns", {})
        
        analysis_prompt = f"""
Analyze these governan ce patterns and identify SYSTEMIC policy issues:

PATTERNS (last 30 days):
{json.dumps(patterns, indent=2)}

DEEP ANALYSIS:
1. Which categories are problematic? Why?
2. Which wards need intervention? Why?
3. Are high-urgency complaints ignored?
4. What's the root cause of delays?
5. Is there systemic negligence?

Return JSON:
{{
  "critical_issues": ["issue1", "issue2"],
  "affected_wards": ["ward", "count"],
  "systemic_root_causes": ["cause1", "cause2"],
  "severity_level": "low|medium|high|critical",
  "urgency_priority": "routine|important|emergency",
  "governance_gaps": ["gap1", "gap2"],
  "policy_failures": ["failure1", "failure2"]
}}
"""
        
        response = await call_groq(analysis_prompt)
        
        try:
            analysis = json.loads(response)
            self.thought_log.add_observation("systemic_analysis", analysis)
            return {
                "analysis": analysis,
                "ready": True
            }
        except Exception as e:
            logger.error(f"Systemic analysis failed: {e}")
            return {"analysis": {}, "ready": False}
    
    async def _generate_policy_brief(self, data: Dict) -> Dict:
        """Generate actionable governance brief"""
        from utils.groq_client import call_groq
        
        patterns = data.get("patterns", {})
        analysis = data.get("analysis", {})
        
        brief_prompt = f"""
Generate an executive governance brief for the administration:

CURRENT STATE:
{json.dumps(patterns, indent=2)}

ISSUES IDENTIFIED:
{json.dumps(analysis, indent=2)}

CREATE A BRIEF WITH:
1. SITUATION: Current state in 2 sentences
2. PROBLEMS: Top 3 critical issues
3. IMPACT: Human/systemic impact
4. ROOT CAUSES: Why does this happen?
5. RECOMMENDATIONS: 3-5 specific actions
6. METRICS: How to measure success
7. TIMELINE: When to implement

Format as clear executive summary.
"""
        
        brief_text = await call_groq(brief_prompt)
        
        return {
            "brief": brief_text,
            "recommendations": analysis.get("policy_failures", []),
            "priority": analysis.get("urgency_priority", "routine")
        }
    
    async def generate_governance_brief(self, scope: str = "all_wards") -> Dict:
        """
        Main entry point: Generate full governance intelligence brief
        
        Args:
            scope: "all_wards" or specific "Ward 5"
        
        Returns:
        {
            "brief": "executive summary",
            "critical_issues": [...],
            "recommendations": [...],
            "metrics": { ... },
            "reasoning_trace": { ... }
        }
        """
        
        problem = f"""
Generate a comprehensive governance intelligence brief for {scope}.
Analyze patterns, identify systemic issues, and recommend interventions.
"""
        
        context = {
            "scope": scope,
            "timestamp": datetime.now().isoformat()
        }
        
        # THINK
        approaches = await self.think(problem, context)
        self.thought_log.add_thought(f"Policy analysis approaches: {approaches}")
        
        # ACT - Fetch patterns
        patterns_data = await self.act(
            ActionType.RETRIEVE_DATA,
            {"days": 30, "scope": scope}
        )
        
        # ACT - Analyze issues
        analysis_data = await self.act(
            ActionType.ANALYZE,
            patterns_data
        )
        
        # ACT - Generate brief
        brief_data = await self.act(
            ActionType.GENERATE_INSIGHT,
            {**patterns_data, **analysis_data}
        )
        
        return {
            "success": True,
            "agent": "PolicyAgent",
            "scope": scope,
            "result": {
                "brief": brief_data.get("brief", ""),
                "patterns": patterns_data.get("patterns", {}),
                "issues": analysis_data.get("analysis", {}),
                "recommendations": brief_data.get("recommendations", []),
                "priority": brief_data.get("priority", "routine")
            },
            "reasoning_trace": self.thought_log.to_dict(),
            "iterations": self.iteration,
            "generated_at": datetime.now().isoformat()
        }
