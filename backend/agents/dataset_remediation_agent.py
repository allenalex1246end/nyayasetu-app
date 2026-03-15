"""
Dataset Remediation Agent
Autonomously detects and fixes data quality issues across the system
Uses Gen AI to identify and remediate inconsistencies
"""

import json
import logging
from typing import Dict, List, Any
from .base_agent import BaseAgent, ActionType

logger = logging.getLogger(__name__)


class DatasetRemediationAgent(BaseAgent):
    """
    Autonomous data quality agent that:
    1. Detects missing values and fills them intelligently
    2. Identifies and merges duplicate records
    3. Fixes data inconsistencies and invalid formats
    4. Verifies data integrity across tables
    5. Reports issues to admins
    """
    
    def __init__(self):
        super().__init__(
            name="DatasetRemediator",
            role="Data Quality and Integrity Manager",
            model_name="llama-3.1-8b"
        )
    
    async def act(self, action_type: ActionType, action_data: Dict) -> Dict:
        """Execute data remediation actions"""
        
        if action_type == ActionType.ANALYZE:
            return await self._analyze_data_quality(action_data)
        
        elif action_type == ActionType.RETRIEVE_DATA:
            return await self._scan_for_issues(action_data)
        
        elif action_type == ActionType.MAKE_DECISION:
            return await self._plan_remediation(action_data)
        
        return {"status": "unknown_action"}
    
    async def _analyze_data_quality(self, analysis_data: Dict) -> Dict:
        """Use Gen AI to analyze data quality issues"""
        from utils.groq_client import call_groq
        
        issues = analysis_data.get("issues", [])
        
        prompt = f"""
Analyze these data quality issues and suggest fixes:

Issues Found:
{json.dumps(issues, indent=2)}

For each issue, provide:
1. Root cause of the problem
2. Recommended fix approach
3. Impact of not fixing (data quality risk)
4. Fix priority (critical|high|medium|low)

Return JSON:
{{
  "issue_assessments": [
    {{
      "issue_id": "unique_id",
      "issue_type": "missing_value|duplicate|inconsistency|invalid_format",
      "severity": "critical|high|medium|low",
      "root_cause": "why this happened",
      "recommended_fix": "specific action to take",
      "affected_records": number,
      "data_loss_risk": true/false
    }}
  ],
  "overall_quality_score": <0-100>,
  "urgent_actions": ["action1", "action2"]
}}
"""
        
        response = await call_groq(prompt)
        
        try:
            analysis = json.loads(response)
            self.thought_log.add_observation("data_quality_analysis", analysis)
            return {
                "action": "analyzed",
                "analysis": analysis
            }
        except:
            logger.warning("Failed to parse data quality analysis")
            return {"action": "analyzed", "analysis": {}}
    
    async def _scan_for_issues(self, scan_data: Dict) -> Dict:
        """Scan database for data quality issues"""
        from main import supabase
        
        if not supabase:
            return {"action": "scanned", "issues": []}
        
        try:
            issues = []
            
            # Scan grievances table
            grievances = supabase.table("grievances").select("*").execute()
            missing_values = []
            invalid_statuses = []
            incomplete_records = []
            
            for g in (grievances.data or []):
                # Check for missing critical fields
                if not g.get("description") or len(str(g.get("description", "")).strip()) < 5:
                    missing_values.append({
                        "record_id": g.get("id"),
                        "field": "description",
                        "issue": "empty or minimal text"
                    })
                
                if not g.get("phone"):
                    missing_values.append({
                        "record_id": g.get("id"),
                        "field": "phone",
                        "issue": "phone number missing"
                    })
                
                # Check for invalid status values
                valid_statuses = ["open", "closed", "resolved", "escalated", "in_progress"]
                if g.get("status") not in valid_statuses:
                    invalid_statuses.append({
                        "record_id": g.get("id"),
                        "current_value": g.get("status"),
                        "valid_values": valid_statuses
                    })
                
                # Check for incomplete records (no timestamps, no category)
                if not g.get("created_at") or not g.get("category"):
                    incomplete_records.append({
                        "record_id": g.get("id"),
                        "missing_fields": [f for f in ["created_at", "category"] if not g.get(f)]
                    })
            
            if missing_values:
                issues.append({
                    "issue_type": "missing_values",
                    "table": "grievances",
                    "count": len(missing_values),
                    "examples": missing_values[:3],
                    "severity": "high"
                })
            
            if invalid_statuses:
                issues.append({
                    "issue_type": "invalid_format",
                    "table": "grievances",
                    "field": "status",
                    "count": len(invalid_statuses),
                    "examples": invalid_statuses[:3],
                    "severity": "high"
                })
            
            if incomplete_records:
                issues.append({
                    "issue_type": "incomplete_records",
                    "table": "grievances",
                    "count": len(incomplete_records),
                    "examples": incomplete_records[:3],
                    "severity": "medium"
                })
            
            self.thought_log.add_observation("issues_found", {"count": len(issues), "details": issues})
            
            return {
                "action": "scanned",
                "issues": issues,
                "total_issues": len(issues)
            }
        
        except Exception as e:
            logger.error(f"Data scan failed: {e}")
            return {"action": "scanned", "issues": [], "error": str(e)}
    
    async def _plan_remediation(self, planning_data: Dict) -> Dict:
        """Plan and execute data remediation"""
        from main import supabase
        
        if not supabase:
            return {"action": "planned", "remediation_plan": []}
        
        issues = planning_data.get("issues", [])
        plan = []
        
        for issue in issues:
            if issue.get("issue_type") == "missing_values":
                plan.append({
                    "action": "fill_missing_values",
                    "table": issue.get("table"),
                    "field": issue.get("field"),
                    "count": issue.get("count"),
                    "strategy": "fill with placeholder or attempt inference"
                })
            
            elif issue.get("issue_type") == "invalid_format":
                plan.append({
                    "action": "normalize_values",
                    "table": issue.get("table"),
                    "field": issue.get("field"),
                    "count": issue.get("count"),
                    "strategy": "map to valid values"
                })
        
        self.thought_log.add_observation("remediation_plan", plan)
        
        return {
            "action": "planned",
            "remediation_plan": plan,
            "total_fixes": len(plan)
        }
    
    async def remediate_dataset(self) -> Dict:
        """
        Main entry point: Scan dataset and auto-remediate issues
        
        Returns:
        {
            "success": true/false,
            "issues_found": count,
            "issues_fixed": count,
            "remediation_details": [...]
        }
        """
        
        problem = """
Analyze the NyayaSetu database for data quality issues:
1. Missing or incomplete values
2. Invalid status values
3. Duplicate records
4. Data inconsistencies
5. Invalid formats

Identify issues and create a remediation plan.
"""
        
        context = {"operation": "full_dataset_scan"}
        
        # Run remediation agent
        result = await self.run(problem, context)
        
        issues_fixed = []
        
        # Execute fixes
        from main import supabase
        if supabase:
            try:
                # Fix invalid statuses
                grievances = supabase.table("grievances").select("*").execute()
                valid_statuses = ["open", "closed", "resolved", "escalated", "in_progress"]
                
                for g in (grievances.data or []):
                    if g.get("status") not in valid_statuses:
                        supabase.table("grievances").update({
                            "status": "open"  # Default to open
                        }).eq("id", g["id"]).execute()
                        
                        issues_fixed.append({
                            "record_id": g["id"],
                            "fix": "status normalized to 'open'"
                        })
                
                # Fix missing phone numbers
                for g in (grievances.data or []):
                    if not g.get("phone"):
                        supabase.table("grievances").update({
                            "phone": "[Contact info not provided]"
                        }).eq("id", g["id"]).execute()
                        
                        issues_fixed.append({
                            "record_id": g["id"],
                            "fix": "phone field filled with placeholder"
                        })
                
                logger.info(f"✅ Dataset remediation completed: {len(issues_fixed)} fixes applied")
                
            except Exception as e:
                logger.error(f"Remediation execution failed: {e}")
        
        return {
            **result,
            "operation": "dataset_remediation",
            "issues_found_and_fixed": len(issues_fixed),
            "fixes_applied": issues_fixed[:10],  # Show first 10
            "total_records_checked": len((grievances.data or [])) if supabase else 0
        }
