# app/orchestrator_graph.py
from langgraph.graph import StateGraph, END
from app.graph_state import AgentState
from app.graph_nodes import WorkflowNodes
from app.agents.clients import *

class MasterAgentGraph:
    """LangGraph-based Master Orchestrator"""
    
    def __init__(
        self,
        data_agent: DataAgentClient,
        diagnosis_agent: DiagnosisAgentClient,
        voice_agent: VoiceAgentClient,
        scheduling_agent: SchedulingAgentClient,
        feedback_agent: FeedbackAgentClient,
        mfg_agent: ManufacturingAgentClient,
    ):
        self.nodes = WorkflowNodes(
            data_agent=data_agent,
            diagnosis_agent=diagnosis_agent,
            voice_agent=voice_agent,
            scheduling_agent=scheduling_agent,
            feedback_agent=feedback_agent,
            mfg_agent=mfg_agent,
        )
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the workflow graph"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze", self.nodes.analyze_telematics)
        workflow.add_node("predict", self.nodes.predict_failure)
        workflow.add_node("craft_script", self.nodes.craft_voice_script)
        workflow.add_node("call_customer", self.nodes.call_customer)
        workflow.add_node("propose_appointment", self.nodes.propose_appointment)
        workflow.add_node("confirm_appointment", self.nodes.confirm_appointment)
        workflow.add_node("request_feedback", self.nodes.request_feedback)
        workflow.add_node("submit_rca", self.nodes.submit_rca)
        workflow.add_node("log_low_risk", self.nodes.log_low_risk)
        
        # Define flow
        workflow.set_entry_point("analyze")
        
        # Linear flow: analyze -> predict
        workflow.add_edge("analyze", "predict")
        
        # Conditional routing based on risk level
        workflow.add_conditional_edges(
            "predict",
            self._route_by_risk,
            {
                "critical": "craft_script",
                "high": "craft_script",
                "medium": "craft_script",
                "low": "log_low_risk"
            }
        )
        
        # Voice interaction flow
        workflow.add_edge("craft_script", "call_customer")
        
        # Conditional routing after customer call
        workflow.add_conditional_edges(
            "call_customer",
            self._route_after_call,
            {
                "schedule": "propose_appointment",
                "rca_only": "submit_rca",
                "end": END
            }
        )
        
        # Scheduling flow
        workflow.add_edge("propose_appointment", "confirm_appointment")
        
        # After confirmation: parallel-ish (we'll do sequential for simplicity)
        workflow.add_edge("confirm_appointment", "request_feedback")
        workflow.add_edge("request_feedback", "submit_rca")
        
        # End points
        workflow.add_edge("submit_rca", END)
        workflow.add_edge("log_low_risk", END)
        
        return workflow.compile()
    
    def _route_by_risk(self, state: AgentState) -> str:
        """Route based on risk level"""
        risk_level = state["risk_level"]
        
        if risk_level == "CRITICAL":
            return "critical"
        elif risk_level == "HIGH":
            return "high"
        elif risk_level == "MEDIUM":
            return "medium"
        else:
            return "low"
    
    def _route_after_call(self, state: AgentState) -> str:
        """Route based on customer response and risk level"""
        accepted = state.get("customer_accepted", False)
        risk_level = state["risk_level"]
        
        # Critical: always schedule (even if declined)
        if risk_level == "CRITICAL":
            return "schedule"
        
        # High: schedule if accepted
        if risk_level == "HIGH" and accepted:
            return "schedule"
        
        # High but declined: still submit RCA
        if risk_level == "HIGH" and not accepted:
            return "rca_only"
        
        # Medium: just monitor (end)
        if risk_level == "MEDIUM":
            return "end"
        
        return "end"
    
    async def process_telematics(self, t: Telematics) -> dict:
        """Execute the graph"""
        initial_state: AgentState = {
            "telematics": t,
            "analysis": None,
            "issue": None,
            "risk_level": None,
            "voice_script": None,
            "customer_accepted": None,
            "appointment_proposal": None,
            "appointment_confirmed": None,
            "feedback_requested": None,
            "rca_submitted": None,
            "actions": {},
            "errors": []
        }
        
        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        # Store state
        from app.state import VEHICLE_STATE
        VEHICLE_STATE[t.vehicle_id] = {
            "last_telematics": t.model_dump(),
            "analysis": final_state["analysis"],
            "issue": final_state["issue"].model_dump() if final_state["issue"] else None,
            "timestamp": t.timestamp,
        }
        
        return final_state["actions"]