"""
Base Agent Framework - ReAct Pattern (Reasoning + Acting)
All agents inherit from this to ensure consistent architecture
"""

import json
import logging
from enum import Enum
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions an agent can take"""
    ANALYZE = "analyze"
    CHECK_RULES = "check_rules"
    RETRIEVE_DATA = "retrieve_data"
    CONSULT_EXPERT = "consult_expert"
    MAKE_DECISION = "make_decision"
    GENERATE_INSIGHT = "generate_insight"
    ESCALATE = "escalate"


class ThoughtLog:
    """Record of agent's reasoning process"""
    
    def __init__(self):
        self.thoughts: List[str] = []
        self.observations: List[Dict] = []
        self.actions: List[Dict] = []
        self.decisions: List[Dict] = []
        self.start_time = datetime.now()
    
    def add_thought(self, thought: str):
        """Add a reasoning step"""
        self.thoughts.append(f"[{datetime.now().isoformat()}] {thought}")
    
    def add_observation(self, key: str, value: Any):
        """Record observation from data retrieval"""
        self.observations.append({
            "key": key,
            "value": value,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_action(self, action_type: ActionType, details: Dict):
        """Record action taken"""
        self.actions.append({
            "type": action_type.value,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_decision(self, decision: str, reasoning: str, confidence: float):
        """Record final decision"""
        self.decisions.append({
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self):
        """Export reasoning process"""
        return {
            "thoughts": self.thoughts,
            "observations": self.observations,
            "actions": self.actions,
            "decisions": self.decisions,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds()
        }


class BaseAgent:
    """
    Base agent implementing ReAct pattern (Reasoning + Acting)
    
    Flow:
    1. THINK (Reasoning): Analyze problem, consider options
    2. ACT (Acting): Retrieve data, call tools, make observations
    3. REFLECT: Update understanding based on observations
    4. DECIDE: Make well-reasoned decision with confidence
    """
    
    def __init__(self, name: str, role: str, model_name: str = "llama-3.1-8b"):
        self.name = name
        self.role = role
        self.model_name = model_name
        self.thought_log = ThoughtLog()
        self.max_iterations = 5  # Prevent infinite loops
        self.iteration = 0
    
    async def think(self, problem: str, context: Dict = None) -> List[str]:
        """
        THINK phase: Reason about the problem
        Returns: List of candidate approaches
        """
        context_str = json.dumps(context or {}, indent=2)
        prompt = f"""
You are {self.name}, a {self.role} AI agent.

Problem to solve:
{problem}

Context:
{context_str}

Think step-by-step. What approaches could solve this? List 3-5 candidate strategies.
Consider all angles: efficiency, fairness, rules, edge cases.

Return JSON:
{{
  "problem_understanding": "brief restatement",
  "key_considerations": ["point1", "point2", ...],
  "candidate_approaches": ["approach1", "approach2", ...]
}}
"""
        from utils.groq_client import call_groq
        
        response = await call_groq(prompt)
        self.thought_log.add_thought(f"Problem analysis: {problem[:50]}...")
        
        try:
            data = json.loads(response)
            self.thought_log.add_observation("problem_understanding", data.get("problem_understanding"))
            return data.get("candidate_approaches", [])
        except:
            return []
    
    async def act(self, action_type: ActionType, action_data: Dict) -> Dict:
        """
        ACT phase: Execute action and get observations
        Returns: Observations/results
        """
        self.thought_log.add_action(action_type, action_data)
        
        # Child classes override this with specific implementations
        return {"status": "action_executed", "data": action_data}
    
    async def reflect(self, observations: List[Dict], previous_decisions: List[Dict] = None) -> str:
        """
        REFLECT phase: Interpret observations and update reasoning
        Returns: Updated understanding
        """
        obs_str = json.dumps(observations, indent=2)
        prev_str = json.dumps(previous_decisions or [], indent=2)
        
        prompt = f"""
Given these observations:
{obs_str}

Previous unsuccessful attempts:
{prev_str}

What new insights do these reveal? How should this change our approach?
Return a brief reflection (2-3 sentences).
"""
        from utils.groq_client import call_groq
        
        reflection = await call_groq(prompt)
        self.thought_log.add_thought(f"Reflection: {reflection}")
        return reflection
    
    async def decide(self, analysis: Dict, confidence_threshold: float = 0.7) -> Dict:
        """
        DECIDE phase: Make final decision with confidence score
        Returns: Decision + confidence + reasoning
        """
        analysis_str = json.dumps(analysis, indent=2)
        
        prompt = f"""
Based on this analysis:
{analysis_str}

Make a clear decision. Be confident but realistic about uncertainty.

Return JSON:
{{
  "decision": "the decision statement",
  "reasoning": "why this is the right call",
  "confidence": <0.0 to 1.0>,
  "assumptions": ["assumption1", "assumption2"],
  "risks": ["risk1", "risk2"],
  "alternatives_rejected": ["why alt1 was rejected", ...]
}}
"""
        from utils.groq_client import call_groq
        
        response = await call_groq(prompt)
        
        try:
            decision = json.loads(response)
            self.thought_log.add_decision(
                decision["decision"],
                decision["reasoning"],
                decision.get("confidence", 0.5)
            )
            return decision
        except:
            return {
                "decision": "Unable to decide",
                "reasoning": "Error in decision logic",
                "confidence": 0.0
            }
    
    async def run(self, problem: str, context: Dict = None) -> Dict:
        """
        Main agent loop: THINK → ACT → REFLECT → DECIDE
        Returns: Final decision + complete reasoning trace
        """
        self.iteration = 0
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            logger.info(f"{self.name} iteration {self.iteration}")
            
            # THINK
            approaches = await self.think(problem, context)
            if not approaches:
                break
            
            # ACT (child class implements specific actions)
            observations = await self.act(ActionType.RETRIEVE_DATA, {"approaches": approaches})
            
            # REFLECT
            if self.iteration > 1:
                reflection = await self.reflect(
                    [observations],
                    self.thought_log.decisions
                )
            else:
                reflection = "Initial analysis complete"
            
            # DECIDE (on final iteration or if confident)
            if self.iteration >= self.max_iterations or observations.get("ready_to_decide"):
                analysis = {
                    "problem": problem,
                    "approaches": approaches,
                    "observations": observations,
                    "reflection": reflection,
                    "context": context
                }
                decision = await self.decide(analysis)
                
                return {
                    "success": True,
                    "agent": self.name,
                    "role": self.role,
                    "result": decision,
                    "reasoning_trace": self.thought_log.to_dict(),
                    "iterations": self.iteration
                }
        
        return {
            "success": False,
            "agent": self.name,
            "error": "Max iterations reached without decision",
            "reasoning_trace": self.thought_log.to_dict(),
        }
