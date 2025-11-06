from typing import Dict, Any
from app.schemas import (
    Telematics, PredictedIssue, VoiceScript, AppointmentProposal, 
    AppointmentConfirmation, FeedbackPrompt, RCAInsight
)

class DataAgentClient:
    async def analyze(self, t: Telematics) -> Dict[str, Any]:
        raise NotImplementedError

class DiagnosisAgentClient:
    async def predict(self, t: Telematics) -> PredictedIssue:
        raise NotImplementedError

class VoiceAgentClient:
    async def craft_script(self, issue: PredictedIssue) -> VoiceScript:
        raise NotImplementedError
    async def call_owner(self, vehicle_id: str, script: VoiceScript) -> bool:
        raise NotImplementedError

class SchedulingAgentClient:
    async def propose(self, vehicle_id: str) -> AppointmentProposal:
        raise NotImplementedError
    async def confirm(self, vehicle_id: str, slot: str) -> AppointmentConfirmation:
        raise NotImplementedError

class FeedbackAgentClient:
    async def request_feedback(self, booking_id: str, vehicle_id: str) -> FeedbackPrompt:
        raise NotImplementedError

class ManufacturingAgentClient:
    async def submit_rca(self, insight: RCAInsight) -> bool:
        raise NotImplementedError