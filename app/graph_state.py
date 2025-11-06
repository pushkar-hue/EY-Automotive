# app/graph_state.py
from typing import TypedDict, Optional, Dict, Any, List
from app.schemas import Telematics, PredictedIssue

class AgentState(TypedDict):
    """Shared state passed between all nodes"""
    # Input
    telematics: Telematics
    
    # Analysis results
    analysis: Optional[Dict[str, Any]]
    issue: Optional[PredictedIssue]
    risk_level: Optional[str]
    
    # Voice interaction
    voice_script: Optional[Dict[str, Any]]
    customer_accepted: Optional[bool]
    
    # Scheduling
    appointment_proposal: Optional[Dict[str, Any]]
    appointment_confirmed: Optional[Dict[str, Any]]
    
    # Feedback & RCA
    feedback_requested: Optional[bool]
    rca_submitted: Optional[bool]
    
    # Actions taken
    actions: Dict[str, Any]
    
    # Error handling
    errors: List[str]