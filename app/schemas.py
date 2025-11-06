from datetime import datetime
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field

class Telematics(BaseModel):
    vehicle_id: str
    timestamp: datetime
    mileage_km: float
    engine_temp_c: float
    rpm: float
    brake_pad_mm: float
    oil_quality_pct: float
    dtc_codes: List[str] = []

class PredictedIssue(BaseModel):
    vehicle_id: str
    component: Literal["engine", "brakes", "battery", "injector", "coolant", "oil"]
    risk_score: float = Field(ge=0, le=1)
    horizon_days: int
    rationale: str

class VoiceScript(BaseModel):
    openers: str
    summary: str
    recommendation: str
    ask_to_schedule: str

class AppointmentProposal(BaseModel):
    vehicle_id: str
    options: List[str]  # ISO times as strings for simplicity
    center: str

class AppointmentConfirmation(BaseModel):
    vehicle_id: str
    chosen_slot: str
    center: str
    booking_id: str

class FeedbackPrompt(BaseModel):
    vehicle_id: str
    booking_id: str
    message: str

class RCAInsight(BaseModel):
    title: str
    summary: str
    actions: List[str]

class UEBAEvent(BaseModel):
    ts: float
    actor: str  # which agent
    action: str
    resource: str
    details: Dict[str, Any] = {}

class UEBAAlert(BaseModel):
    ts: float
    severity: Literal["low", "medium", "high"]
    actor: str
    reason: str
    event: UEBAEvent