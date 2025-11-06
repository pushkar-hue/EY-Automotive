from typing import Dict, Any
from app.schemas import Telematics, RCAInsight
from app.state import VEHICLE_STATE
from app.ueba import UEBA
from app.agents.clients import (
    DataAgentClient, DiagnosisAgentClient, VoiceAgentClient,
    SchedulingAgentClient, FeedbackAgentClient, ManufacturingAgentClient
)

class MasterAgent:
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

    async def process_telematics(self, t: Telematics) -> Dict[str, Any]:
        UEBA.log("master", "read", "telematics:read", {"vehicle_id": t.vehicle_id})

        # 1) Data analysis (optional anomalies)
        analysis = await self.data_agent.analyze(t)

        # 2) Predict failure
        issue = await self.diagnosis_agent.predict(t)
        VEHICLE_STATE[t.vehicle_id] = {
            "last_telematics": t.model_dump(),
            "analysis": analysis,
            "issue": issue.model_dump(),
        }

        # 3) Decide whether to engage customer
        actions: Dict[str, Any] = {"analysis": analysis, "issue": issue.model_dump()}
        if issue.risk_score >= 0.6:
            # a) craft voice script
            script = await self.voice_agent.craft_script(issue)
            # b) call owner
            accepted = await self.voice_agent.call_owner(t.vehicle_id, script)
            actions["voice"] = {"accepted": accepted, "script": script.model_dump()}

            if accepted:
                # 4) Scheduling
                proposal = await self.scheduling_agent.propose(t.vehicle_id)
                # naive: pick the first slot
                chosen = proposal.options[0]
                confirmation = await self.scheduling_agent.confirm(t.vehicle_id, chosen)
                actions["scheduling"] = {
                    "proposal": proposal.model_dump(),
                    "confirmation": confirmation.model_dump(),
                }

                # 5) Post-service feedback (simulated immediate request)
                feedback = await self.feedback_agent.request_feedback(confirmation.booking_id, t.vehicle_id)
                actions["feedback"] = feedback.model_dump()

                # 6) RCA/CAPA insight to manufacturing (simple demo rule)
                insight = RCAInsight(
                    title=f"Recurring {issue.component} alerts in segment",
                    summary=(
                        f"Vehicle {t.vehicle_id} shows {issue.component} risk {issue.risk_score}. "
                        f"Telemetry anomalies: {list(analysis.get('anomalies', {}).keys())}."
                    ),
                    actions=[
                        "Investigate supplier batch",
                        "Review assembly torque specs",
                        "Update preventive maintenance checklist",
                    ],
                )
                await self.mfg_agent.submit_rca(insight)
                actions["rca"] = insight.model_dump()
        else:
            actions["voice"] = {"accepted": False, "reason": "Risk below engagement threshold"}

        return actions