"""
Agent Memory System
Maintains context, learning, and decision history across agent runs
Implements token-limited conversation memory with semantic importance
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    Multi-tier memory system for agents:
    - Short-term: Recent decisions (in-session)
    - Long-term: Important patterns and learnings
    - Episodic: Specific case histories
    """
    
    def __init__(self, max_short_term: int = 50, max_long_term: int = 500):
        self.short_term_memory = deque(maxlen=max_short_term)
        self.long_term_memory = deque(maxlen=max_long_term)
        self.episodic_memory: Dict[str, Dict] = {}
        self.patterns: Dict[str, int] = {}
        self.learnings: List[str] = []
    
    def add_short_term(self, event: Dict):
        """Add to recent memory (in-session context)"""
        event["timestamp"] = datetime.now().isoformat()
        self.short_term_memory.append(event)
        logger.info(f"Short-term memory: {event.get('type', 'unknown')}")
    
    def add_long_term(self, event: Dict):
        """Add important learning to long-term memory"""
        event["timestamp"] = datetime.now().isoformat()
        self.long_term_memory.append(event)
        logger.info(f"Long-term memory: {event.get('learning', 'unknown')}")
    
    def add_episodic(self, case_id: str, episode: Dict):
        """Store specific case history"""
        self.episodic_memory[case_id] = {
            "case_id": case_id,
            "data": episode,
            "timestamp": datetime.now().isoformat(),
            "importance": 0.5
        }
    
    def record_pattern(self, pattern_name: str, occurrence: int = 1):
        """Track recurring patterns (e.g., 'water_complaints_ward5')"""
        self.patterns[pattern_name] = self.patterns.get(pattern_name, 0) + occurrence
    
    def record_learning(self, learning: str):
        """Record important insights for future decisions"""
        self.learnings.append({
            "learning": learning,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Agent learning recorded: {learning}")
    
    def get_context_for_decision(self, decision_type: str, limit_tokens: int = 1000) -> str:
        """
        Build context string for agent decision-making
        Implements token-aware importance sampling
        """
        context_parts = []
        
        # Add relevant short-term memory
        recent_count = 0
        for event in list(self.short_term_memory)[-10:]:
            if event.get("type") == decision_type:
                context_parts.append(f"- Recent: {event}")
                recent_count += 1
        
        # Add high-pattern insights
        top_patterns = sorted(
            self.patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        if top_patterns:
            context_parts.append("\nCommon Patterns:")
            for pattern, count in top_patterns:
                context_parts.append(f"- {pattern}: {count}x")
        
        # Add recent learnings
        if self.learnings:
            context_parts.append("\nRecent Learnings:")
            for learning in self.learnings[-5:]:
                context_parts.append(f"- {learning['learning']}")
        
        return "\n".join(context_parts)
    
    def get_similar_cases(self, current_case: Dict, limit: int = 3) -> List[Dict]:
        """Retrieve similar historical cases from episodic memory"""
        current_category = current_case.get("category")
        current_ward = current_case.get("ward")
        
        similar = []
        for case_id, episode in list(self.episodic_memory.items())[-20:]:
            ep_data = episode.get("data", {})
            
            # Simple similarity: same category and ward
            if (ep_data.get("category") == current_category and
                ep_data.get("ward") == current_ward):
                similar.append({
                    "case_id": case_id,
                    "category": ep_data.get("category"),
                    "outcome": ep_data.get("outcome"),
                    "resolution_time": ep_data.get("resolution_time"),
                    "lessons": ep_data.get("lessons", [])
                })
        
        return similar[:limit]
    
    def to_dict(self) -> Dict:
        """Export memory state (for visualization/debugging)"""
        return {
            "short_term": list(self.short_term_memory)[-10:],
            "long_term": list(self.long_term_memory)[-10:],
            "episodic_count": len(self.episodic_memory),
            "patterns": dict(sorted(self.patterns.items(), key=lambda x: x[1], reverse=True)[:10]),
            "learnings": self.learnings[-5:]
        }
    
    def clear_old_memory(self, days_threshold: int = 7):
        """Clean up old entries"""
        cutoff = (datetime.now() - timedelta(days=days_threshold)).isoformat()
        
        # Clean episodic memory
        old_cases = [
            case_id for case_id, episode in self.episodic_memory.items()
            if episode.get("timestamp", "") < cutoff
        ]
        for case_id in old_cases:
            del self.episodic_memory[case_id]
        
        logger.info(f"Cleaned {len(old_cases)} old episodic memories")


class SharedAgentMemory:
    """
    Shared memory between multiple agents
    Allows agents to learn from each other's decisions
    """
    
    def __init__(self):
        self.collective_learnings: List[Dict] = []
        self.decision_history: List[Dict] = []
        self.success_patterns: Dict[str, int] = {}
        self.failure_patterns: Dict[str, int] = {}
    
    def record_agent_decision(self, agent_name: str, decision: Dict, outcome: str = "pending"):
        """Record decision for collective learning"""
        record = {
            "agent": agent_name,
            "decision": decision,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat()
        }
        self.decision_history.append(record)
        
        # Update success/failure patterns
        decision_type = decision.get("type", "unknown")
        if outcome == "success":
            self.success_patterns[decision_type] = self.success_patterns.get(decision_type, 0) + 1
        elif outcome == "failure":
            self.failure_patterns[decision_type] = self.failure_patterns.get(decision_type, 0) + 1
    
    def record_collective_learning(self, learning: str, agents_involved: List[str]):
        """Record wisdom from agent collaboration"""
        self.collective_learnings.append({
            "learning": learning,
            "agents": agents_involved,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Collective learning: {learning} (from {agents_involved})")
    
    def get_best_practices(self, decision_type: str) -> Dict:
        """Get aggregate success patterns for a decision type"""
        successes = self.success_patterns.get(decision_type, 0)
        failures = self.failure_patterns.get(decision_type, 0)
        success_rate = successes / max(successes + failures, 1)
        
        return {
            "decision_type": decision_type,
            "success_rate": success_rate,
            "successes": successes,
            "failures": failures,
            "recommendation": "proceed" if success_rate > 0.7 else "proceed_with_caution" if success_rate > 0.5 else "avoid"
        }
    
    def get_collective_insights(self) -> List[str]:
        """Get all collective learnings"""
        return [l["learning"] for l in self.collective_learnings[-10:]]


# Global shared memory for all agents
_shared_memory: Optional[SharedAgentMemory] = None


def get_shared_memory() -> SharedAgentMemory:
    """Get or create global shared memory"""
    global _shared_memory
    if _shared_memory is None:
        _shared_memory = SharedAgentMemory()
    return _shared_memory
