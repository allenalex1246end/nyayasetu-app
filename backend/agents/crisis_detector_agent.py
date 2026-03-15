"""
Crisis Detection Agent
Autonomously monitors for urgent situations and sends alerts to officers
Uses Gen AI to detect patterns indicating crises
"""

import json
import logging
from typing import Dict, Any
from .base_agent import BaseAgent, ActionType

logger = logging.getLogger(__name__)


class CrisisDetectorAgent(BaseAgent):
    """
    Detects crisis situations and alerts officers:
    1. Health/safety emergencies (urgency level 5)
    2. Multiple complaints in same ward (systemic issue)
    3. System failures or escalations
    4. Sends automated emails to assigned officers
    """
    
    def __init__(self):
        super().__init__(
            name="CrisisDetector",
            role="Crisis Monitoring and Alert System",
            model_name="llama-3.1-8b"
        )
    
    async def act(self, action_type: ActionType, action_data: Dict) -> Dict:
        """Execute crisis detection actions"""
        
        if action_type == ActionType.ANALYZE:
            return await self._analyze_for_crisis(action_data)
        
        elif action_type == ActionType.RETRIEVE_DATA:
            return await self._get_ward_patterns(action_data)
        
        elif action_type == ActionType.MAKE_DECISION:
            return await self._decide_alert_level(action_data)
        
        return {"status": "unknown_action"}
    
    async def _analyze_for_crisis(self, grievance_data: Dict) -> Dict:
        """Use Gen AI to analyze if this grievance indicates a crisis"""
        from utils.groq_client import call_groq
        
        prompt = f"""
Analyze if this grievance indicates a CRISIS situation requiring immediate officer alert:

Grievance:
- Description: {grievance_data.get('description', '')}
- Ward: {grievance_data.get('ward', 'Unknown')}
- Category: {grievance_data.get('category', 'general')}
- Phone: {grievance_data.get('phone', 'N/A')}
- Urgency: {grievance_data.get('urgency', 1)}/5

CRISIS CRITERIA (return JSON):
{{
  "is_critical": boolean,
  "crisis_type": "health_emergency|multiple_complaints|system_failure|escalation|none",
  "severity": "critical|high|medium|low",
  "reasoning": "why this is/isn't a crisis",
  "immediate_action": "what officer should do",
  "keywords_detected": ["keyword1", "keyword2"]
}}

Keywords indicating CRISIS:
- Health/medical emergency, injury, sickness, health hazard
- Death, injury requiring medical attention
- System outage, infrastructure failure
- Repeated complaints about same issue
- Violence or threats
- Environmental hazard
"""
        
        response = await call_groq(prompt)
        
        try:
            analysis = json.loads(response)
            self.thought_log.add_observation("crisis_analysis", analysis)
            return {
                "action": "analyzed",
                "crisis_analysis": analysis
            }
        except:
            logger.warning("Failed to parse crisis analysis")
            return {"action": "analyzed", "crisis_analysis": {}}
    
    async def _get_ward_patterns(self, retrieval_data: Dict) -> Dict:
        """Retrieve patterns from same ward to detect systemic issues"""
        from main import supabase
        
        if not supabase:
            return {"action": "data_retrieved", "patterns": {}}
        
        try:
            ward = retrieval_data.get("ward", "")
            category = retrieval_data.get("category", "")
            
            # Get complaints from same ward in last 48 hours
            recent = supabase.table("grievances").select("*").eq("ward", ward).limit(50).execute()
            
            # Count by category
            category_counts = {}
            for g in (recent.data or []):
                cat = g.get("category", "other")
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # Get status distribution
            open_count = len([g for g in (recent.data or []) if g.get("status") == "open"])
            total_count = len(recent.data or [])
            
            patterns = {
                "total_recent_complaints": total_count,
                "open_complaints": open_count,
                "complaint_categories": category_counts,
                "same_category_count": category_counts.get(category, 0),
                "has_systemic_issue": total_count >= 3
            }
            
            self.thought_log.add_observation("ward_patterns", patterns)
            
            return {
                "action": "data_retrieved",
                "patterns": patterns
            }
        except Exception as e:
            logger.error(f"Pattern retrieval failed: {e}")
            return {"action": "data_retrieved", "patterns": {}}
    
    async def _decide_alert_level(self, decision_data: Dict) -> Dict:
        """Decide alert level and which officers to notify"""
        from main import supabase
        
        crisis_analysis = decision_data.get("crisis_analysis", {})
        patterns = decision_data.get("patterns", {})
        grievance_data = decision_data.get("grievance", {})
        
        # Determine if alert needed
        is_critical = crisis_analysis.get("is_critical", False)
        is_systemic = patterns.get("has_systemic_issue", False)
        urgency = grievance_data.get("urgency", 1)
        
        alert_needed = is_critical or is_systemic or urgency >= 5
        
        if not alert_needed:
            return {
                "action": "decision_made",
                "should_alert": False
            }
        
        # Get officers to notify
        ward = grievance_data.get("ward", "")
        officers_to_notify = []
        
        if supabase:
            try:
                result = supabase.table("officers").select("id,email,name,assigned_ward").eq(
                    "assigned_ward", ward
                ).execute()
                officers_to_notify = result.data or []
            except:
                pass
        
        return {
            "action": "decision_made",
            "should_alert": True,
            "crisis_type": crisis_analysis.get("crisis_type"),
            "severity": crisis_analysis.get("severity"),
            "officers_to_alert": officers_to_notify,
            "message": crisis_analysis.get("immediate_action")
        }
    
    async def detect_and_alert_crisis(self, grievance_data: Dict) -> Dict:
        """
        Main entry point: Detect crisis and send alerts
        
        Input:
        {
            "id": "grievance_id",
            "description": "complaint text",
            "ward": "Ward 5",
            "category": "water",
            "phone": "9999999999",
            "urgency": 5
        }
        
        Output:
        {
            "grievance_id": "id",
            "is_crisis": true/false,
            "crisis_type": "...",
            "severity": "...",
            "alerts_sent": number,
            "reasoning_trace": {...}
        }
        """
        
        problem = f"""
Analyze if this is a CRISIS requiring immediate officer alert:
{grievance_data.get('description', '')}
Ward: {grievance_data.get('ward', '')}
Category: {grievance_data.get('category', '')}
Phone: {grievance_data.get('phone', '')}
Urgency: {grievance_data.get('urgency', 1)}/5
"""
        
        context = {
            "grievance": grievance_data,
            "ward": grievance_data.get("ward", "")
        }
        
        # Run analysis
        result = await self.run(problem, context)
        
        # Extract decision
        is_crisis = result.get("result", {}).get("should_alert", False)
        
        # Send alerts if crisis
        alerts_sent = 0
        if is_crisis:
            from utils.email_service import send_crisis_alert_email
            
            crisis_type = result.get("result", {}).get("crisis_type", "unknown")
            severity = result.get("result", {}).get("severity", "high")
            
            crisis_data = {
                "crisis_type": crisis_type,
                "severity": severity,
                "description": result.get("result", {}).get("message", grievance_data.get("description", "")),
                "affected_count": 1
            }
            
            for officer in result.get("result", {}).get("officers_to_alert", []):
                try:
                    success = await send_crisis_alert_email(
                        officer.get("email"),
                        officer.get("name"),
                        crisis_data,
                        grievance_data
                    )
                    if success:
                        alerts_sent += 1
                except Exception as e:
                    logger.error(f"Alert send failed for {officer.get('name')}: {e}")
        
        return {
            **result,
            "grievance_id": grievance_data.get("id"),
            "is_crisis": is_crisis,
            "alerts_sent": alerts_sent,
            "agent_type": "CrisisDetector"
        }
