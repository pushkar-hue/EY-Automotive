# app/graph_nodes.py
from app.graph_state import AgentState
from app.agents.clients import *
from app.schemas import RCAInsight
from app.ueba import UEBA

class WorkflowNodes:
    """All nodes for the LangGraph workflow"""
    
    def __init__(
        self,
        data_agent: DataAgentClient,
        diagnosis_agent: DiagnosisAgentClient,
        voice_agent: VoiceAgentClient,
        scheduling_agent: SchedulingAgentClient,
        feedback_agent: FeedbackAgentClient,
        mfg_agent: ManufacturingAgentClient,
    ):
        self.data_agent = data_agent
        self.diagnosis_agent = diagnosis_agent
        self.voice_agent = voice_agent
        self.scheduling_agent = scheduling_agent
        self.feedback_agent = feedback_agent
        self.mfg_agent = mfg_agent
    
    async def analyze_telematics(self, state: AgentState) -> AgentState:
        """Node 1: Analyze telematics data"""
        UEBA.log("master", "read", "telematics:read", {
            "vehicle_id": state["telematics"].vehicle_id
        })
        
        analysis = await self.data_agent.analyze(state["telematics"])
        
        return {
            **state,
            "analysis": analysis,
            "actions": {**state.get("actions", {}), "analysis": analysis}
        }
    
    async def predict_failure(self, state: AgentState) -> AgentState:
        """Node 2: Predict vehicle failure"""
        issue = await self.diagnosis_agent.predict(state["telematics"])
        
        # Classify risk
        risk_level = self._classify_risk(issue.risk_score)
        
        return {
            **state,
            "issue": issue,
            "risk_level": risk_level,
            "actions": {
                **state.get("actions", {}),
                "issue": issue.model_dump(),
                "risk_level": risk_level
            }
        }
    
    async def craft_voice_script(self, state: AgentState) -> AgentState:
        """Node 3: Create voice script"""
        script = await self.voice_agent.craft_script(
            state["issue"],
            telematics=state["telematics"]
        )
        
        return {
            **state,
            "voice_script": script.model_dump(),
            "actions": {
                **state.get("actions", {}),
                "voice": {"script": script.model_dump()}
            }
        }
    
    async def call_customer(self, state: AgentState) -> AgentState:
        """Node 4: Make customer call"""
        from app.schemas import VoiceScript
        
        script = VoiceScript(**state["voice_script"])
        accepted = await self.voice_agent.call_owner(
            state["telematics"].vehicle_id,
            script
        )
        
        return {
            **state,
            "customer_accepted": accepted,
            "actions": {
                **state.get("actions", {}),
                "voice": {
                    **state.get("actions", {}).get("voice", {}),
                    "accepted": accepted,
                    "urgency": state["risk_level"]
                }
            }
        }
    
    async def propose_appointment(self, state: AgentState) -> AgentState:
        """Node 5: Propose appointment slots"""
        proposal = await self.scheduling_agent.propose(
            state["telematics"].vehicle_id
        )
        
        return {
            **state,
            "appointment_proposal": proposal.model_dump(),
        }
    
    async def confirm_appointment(self, state: AgentState) -> AgentState:
        """Node 6: Confirm appointment"""
        from app.schemas import AppointmentProposal
        
        proposal = AppointmentProposal(**state["appointment_proposal"])
        
        if proposal.options:
            chosen = proposal.options[0]
            confirmation = await self.scheduling_agent.confirm(
                state["telematics"].vehicle_id,
                chosen
            )
            
            is_critical = state["risk_level"] == "CRITICAL"
            auto_scheduled = is_critical and not state.get("customer_accepted", False)
            
            return {
                **state,
                "appointment_confirmed": confirmation.model_dump(),
                "actions": {
                    **state.get("actions", {}),
                    "scheduling": {
                        "proposal": proposal.model_dump(),
                        "confirmation": confirmation.model_dump(),
                        "priority": state["risk_level"].lower(),
                        "auto_scheduled": auto_scheduled
                    }
                }
            }
        
        return state
    
    async def request_feedback(self, state: AgentState) -> AgentState:
        """Node 7: Request customer feedback"""
        if state.get("appointment_confirmed"):
            feedback = await self.feedback_agent.request_feedback(
                state["appointment_confirmed"]["booking_id"],
                state["telematics"].vehicle_id
            )
            
            return {
                **state,
                "feedback_requested": True,
                "actions": {
                    **state.get("actions", {}),
                    "feedback": feedback
                }
            }
        
        return state
    
    async def submit_rca(self, state: AgentState) -> AgentState:
        """Node 8: Submit RCA to manufacturing"""
        anomalies = state.get("analysis", {}).get("anomalies", {})
        anomaly_keys = list(anomalies.keys()) if anomalies else []
        
        t = state["telematics"]
        issue = state["issue"]
        
        insight = RCAInsight(
            title=f"[{state['risk_level']}] {issue.component} alerts - {t.vehicle_model}",
            summary=(
                f"Vehicle {t.vehicle_id} ({t.vehicle_model}) shows {issue.component} "
                f"risk {issue.risk_score:.2f}. Anomalies: {', '.join(anomaly_keys) or 'None'}. "
                f"Days to failure: {issue.days_to_failure}. Mileage: {t.mileage_km}km."
            ),
            actions=self._generate_rca_actions(issue, anomalies, state["risk_level"])
        )
        
        await self.mfg_agent.submit_rca(insight)
        
        return {
            **state,
            "rca_submitted": True,
            "actions": {
                **state.get("actions", {}),
                "rca": insight.model_dump()
            }
        }
    
    async def log_low_risk(self, state: AgentState) -> AgentState:
        """Node: Handle low-risk cases"""
        return {
            **state,
            "actions": {
                **state.get("actions", {}),
                "voice": {
                    "accepted": False,
                    "reason": "Risk below engagement threshold"
                }
            }
        }
    
    def _classify_risk(self, risk_score: float) -> str:
        """Classify risk level"""
        if risk_score >= 0.8:
            return "CRITICAL"
        elif risk_score >= 0.6:
            return "HIGH"
        elif risk_score >= 0.4:
            return "MEDIUM"
        return "LOW"
    
    def _generate_rca_actions(self, issue, anomalies: Dict[str, Any], severity: str) -> list:
        """Generate context-aware RCA actions"""
        actions = []
        
        component_actions = {
            "transmission": [
                "Review transmission fluid supplier quality",
                "Check clutch pack torque specifications",
                "Analyze gear wear patterns across fleet"
            ],
            "brake_system": [
                "Inspect brake pad material batch",
                "Review hydraulic pressure calibration",
                "Check ABS sensor correlation"
            ],
            "engine": [
                "Analyze oil quality and intervals",
                "Review ECU software version",
                "Check turbocharger supplier quality"
            ],
            "battery": [
                "Review charging cycle patterns",
                "Check BMS firmware version",
                "Analyze temperature exposure"
            ]
        }
        
        comp_key = issue.component.lower()
        if comp_key in component_actions:
            actions.extend(component_actions[comp_key])
        else:
            actions.append(f"Investigate {issue.component} supplier")
            actions.append(f"Review {issue.component} assembly procedures")
        
        if severity == "CRITICAL":
            actions.insert(0, "URGENT: Issue service bulletin")
            actions.append("Emergency fleet inspection")
        
        actions.append("Update predictive model with case")
        
        return actions