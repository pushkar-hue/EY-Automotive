from typing import Dict, Any
from app.schemas import Telematics, RCAInsight
from app.state import VEHICLE_STATE
from app.ueba import UEBA
from app.agents.clients import (
    DataAgentClient, DiagnosisAgentClient, VoiceAgentClient,
    SchedulingAgentClient, FeedbackAgentClient, ManufacturingAgentClient
)

class MasterAgent:
    """
    Enhanced Master Orchestrator with Gemini-powered voice agent support
    """
    
    def __init__(
        self,
        data_agent: DataAgentClient,
        diagnosis_agent: DiagnosisAgentClient,
        voice_agent: VoiceAgentClient,  # Now can be GeminiVoiceAgent
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
        
        # Risk thresholds
        self.CRITICAL_THRESHOLD = 0.8
        self.HIGH_THRESHOLD = 0.6
        self.MEDIUM_THRESHOLD = 0.4
    
    async def process_telematics(self, t: Telematics) -> Dict[str, Any]:
        """
        Main orchestration flow with multi-tier risk handling
        """
        UEBA.log("master", "read", "telematics:read", {"vehicle_id": t.vehicle_id})
        
        # 1) Analyze telematics data
        analysis = await self.data_agent.analyze(t)
        
        # 2) Predict failure
        issue = await self.diagnosis_agent.predict(t)
        
        # Store state
        VEHICLE_STATE[t.vehicle_id] = {
            "last_telematics": t.model_dump(),
            "analysis": analysis,
            "issue": issue.model_dump(),
            "timestamp": t.timestamp,
        }
        
        # Initialize response
        actions: Dict[str, Any] = {
            "analysis": analysis,
            "issue": issue.model_dump(),
            "risk_level": self._classify_risk(issue.risk_score)
        }
        
        # 3) Risk-based workflow
        if issue.risk_score >= self.CRITICAL_THRESHOLD:
            actions = await self._handle_critical_risk(t, issue, analysis, actions)
        elif issue.risk_score >= self.HIGH_THRESHOLD:
            actions = await self._handle_high_risk(t, issue, analysis, actions)
        elif issue.risk_score >= self.MEDIUM_THRESHOLD:
            actions = await self._handle_medium_risk(t, issue, analysis, actions)
        else:
            actions["voice"] = {
                "accepted": False,
                "reason": "Risk below engagement threshold"
            }
        
        return actions
    
    def _classify_risk(self, risk_score: float) -> str:
        """Classify risk level"""
        if risk_score >= self.CRITICAL_THRESHOLD:
            return "CRITICAL"
        elif risk_score >= self.HIGH_THRESHOLD:
            return "HIGH"
        elif risk_score >= self.MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "LOW"
    
    async def _handle_critical_risk(
        self, t: Telematics, issue, analysis: Dict[str, Any], actions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """CRITICAL: Immediate action + auto-scheduling"""
        UEBA.log("master", "decision", "critical_path", {
            "vehicle_id": t.vehicle_id,
            "component": issue.component
        })
        
        # 🆕 GEMINI: Pass telematics for richer context
        script = await self.voice_agent.craft_script(issue, telematics=t)
        
        accepted = await self.voice_agent.call_owner(t.vehicle_id, script)
        actions["voice"] = {
            "accepted": accepted,
            "script": script.model_dump(),
            "urgency": "critical"
        }
        
        # Auto-schedule for safety
        proposal = await self.scheduling_agent.propose(t.vehicle_id)
        if proposal.options:
            chosen = proposal.options[0]
            confirmation = await self.scheduling_agent.confirm(t.vehicle_id, chosen)
            actions["scheduling"] = {
                "proposal": proposal.model_dump(),
                "confirmation": confirmation.model_dump(),
                "priority": "critical",
                "auto_scheduled": not accepted
            }
        
        # Submit RCA
        await self._submit_rca(t, issue, analysis, actions, severity="critical")
        
        return actions
    
    async def _handle_high_risk(
        self, t: Telematics, issue, analysis: Dict[str, Any], actions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """HIGH: Customer engagement + scheduling"""
        UEBA.log("master", "decision", "high_risk_path", {
            "vehicle_id": t.vehicle_id,
            "component": issue.component
        })
        
        # 🆕 GEMINI: Pass telematics for context
        script = await self.voice_agent.craft_script(issue, telematics=t)
        
        accepted = await self.voice_agent.call_owner(t.vehicle_id, script)
        actions["voice"] = {
            "accepted": accepted,
            "script": script.model_dump(),
            "urgency": "high"
        }
        
        if accepted:
            proposal = await self.scheduling_agent.propose(t.vehicle_id)
            if proposal.options:
                chosen = proposal.options[0]
                confirmation = await self.scheduling_agent.confirm(t.vehicle_id, chosen)
                actions["scheduling"] = {
                    "proposal": proposal.model_dump(),
                    "confirmation": confirmation.model_dump(),
                }
                
                # Request feedback
                feedback = await self.feedback_agent.request_feedback(
                    confirmation.booking_id, t.vehicle_id
                )
                actions["feedback"] = feedback
                
                # Submit RCA
                await self._submit_rca(t, issue, analysis, actions, severity="high")
        else:
            actions["voice"]["follow_up_required"] = True
        
        return actions
    
    async def _handle_medium_risk(
        self, t: Telematics, issue, analysis: Dict[str, Any], actions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """MEDIUM: Proactive notification"""
        UEBA.log("master", "decision", "medium_risk_path", {
            "vehicle_id": t.vehicle_id,
            "component": issue.component
        })
        
        # 🆕 GEMINI: Pass telematics even for medium risk
        script = await self.voice_agent.craft_script(issue, telematics=t)
        
        actions["voice"] = {
            "notification_sent": True,
            "script": script.model_dump(),
            "urgency": "medium"
        }
        
        actions["monitoring"] = {
            "status": "active",
            "next_check": "24_hours"
        }
        
        return actions
    
    async def _submit_rca(
        self, t: Telematics, issue, analysis: Dict[str, Any],
        actions: Dict[str, Any], severity: str = "high"
    ) -> None:
        """Submit RCA to manufacturing"""
        anomalies = analysis.get('anomalies', {})
        anomaly_keys = list(anomalies.keys()) if anomalies else []
        
        insight = RCAInsight(
            title=f"[{severity.upper()}] {issue.component} alerts - {t.vehicle_model}",
            summary=(
                f"Vehicle {t.vehicle_id} ({t.vehicle_model}) shows {issue.component} "
                f"risk {issue.risk_score:.2f}. Anomalies: {', '.join(anomaly_keys) or 'None'}. "
                f"Days to failure: {issue.days_to_failure}. Mileage: {t.mileage_km}km."
            ),
            actions=self._generate_rca_actions(issue, anomalies, severity)
        )
        
        await self.mfg_agent.submit_rca(insight)
        actions["rca"] = insight.model_dump()
    
    def _generate_rca_actions(
        self, issue, anomalies: Dict[str, Any], severity: str
    ) -> list:
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
        
        if severity == "critical":
            actions.insert(0, "URGENT: Issue service bulletin")
            actions.append("Emergency fleet inspection")
        
        actions.append("Update predictive model with case")
        
        return actions