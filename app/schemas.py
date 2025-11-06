# app/schemas.py
from datetime import datetime
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field

class Telematics(BaseModel):
    vehicle_id: str
    vehicle_model: str = "Unknown Model"  # 🆕 Added with default
    timestamp: datetime
    mileage_km: float
    engine_temp_c: float
    rpm: float
    brake_pad_mm: float
    oil_quality_pct: float
    dtc_codes: List[str] = []

class PredictedIssue(BaseModel):
    vehicle_id: str
    component: Literal["engine", "brakes", "battery", "injector", "coolant", "oil", "transmission", "brake_system"]
    risk_score: float = Field(ge=0, le=1)
    horizon_days: int  # Keep original field
    days_to_failure: int = 0  # 🆕 Add alias for compatibility
    confidence: float = Field(default=0.85, ge=0, le=1)  # 🆕 Added
    rationale: str
    
    def model_post_init(self, __context):
        """Sync days_to_failure with horizon_days"""
        if self.days_to_failure == 0:
            self.days_to_failure = self.horizon_days

class VoiceScript(BaseModel):
    """Updated to match GeminiVoiceAgent output"""
    vehicle_id: str = ""
    script: str  # 🆕 Changed from multiple fields to single script
    urgency: str = "medium"
    estimated_duration_sec: int = 30
    
    # Legacy fields for backward compatibility
    openers: str = ""
    summary: str = ""
    recommendation: str = ""
    ask_to_schedule: str = ""
    
    def model_post_init(self, __context):
        """Auto-fill legacy fields if not provided"""
        if not self.openers and self.script:
            lines = self.script.split('\n\n')
            self.openers = lines[0] if len(lines) > 0 else ""
            self.summary = lines[1] if len(lines) > 1 else ""
            self.recommendation = lines[2] if len(lines) > 2 else ""
            self.ask_to_schedule = lines[-1] if len(lines) > 0 else ""

class AppointmentProposal(BaseModel):
    vehicle_id: str
    options: List[str]  # ISO times as strings
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
    actor: str
    action: str
    resource: str
    details: Dict[str, Any] = {}

class UEBAAlert(BaseModel):
    ts: float
    severity: Literal["low", "medium", "high"]
    actor: str
    reason: str
    event: UEBAEvent