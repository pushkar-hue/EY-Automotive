# app/api.py
from fastapi import FastAPI, HTTPException
from datetime import datetime

from app.config import USE_MOCKS
from app.schemas import Telematics
from app.state import VEHICLE_STATE, APPOINTMENTS, UEBA_LOG, UEBA_ALERTS 
from app.orchestrator_graph import MasterAgentGraph 

if USE_MOCKS:
    from app.agents.mocks import (
        MockDataAgent, MockDiagnosisAgent, GeminiVoiceAgent,
        MockSchedulingAgent, MockFeedbackAgent, MockManufacturingAgent
    )

app = FastAPI(title="Master Orchestrator – LangGraph Edition", version="2.0")

# Initialize LangGraph Master
master = MasterAgentGraph(
    data_agent=MockDataAgent(),
    diagnosis_agent=MockDiagnosisAgent(),
    voice_agent=GeminiVoiceAgent(),
    scheduling_agent=MockSchedulingAgent(),
    feedback_agent=MockFeedbackAgent(),
    mfg_agent=MockManufacturingAgent(),
)

@app.get("/")
async def root():
    return {"ok": True, "service": app.title, "docs": "/docs"}

@app.post("/ingest/telematics")
async def ingest_telematics(t: Telematics):
    """Main entrypoint with LangGraph orchestration"""
    try:
        result = await master.process_telematics(t)
        return {
            "status": "processed",
            "result": result,
            "ueba_alerts": [a.model_dump() for a in UEBA_ALERTS[-5:]]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/state/{vehicle_id}")
async def get_state(vehicle_id: str):
    if vehicle_id not in VEHICLE_STATE:
        raise HTTPException(status_code=404, detail="Unknown vehicle")
    return VEHICLE_STATE[vehicle_id]

@app.get("/appointments/{vehicle_id}")
async def get_appointment(vehicle_id: str):
    appt = APPOINTMENTS.get(vehicle_id)
    if not appt:
        return {"booking": None}
    return appt.model_dump() if appt else None

@app.get("/ueba/logs")
async def ueba_logs(limit: int = 100):
    return [e.model_dump() for e in UEBA_LOG[-limit:]]

@app.get("/ueba/alerts")
async def ueba_alerts(limit: int = 50):
    return [a.model_dump() for a in UEBA_ALERTS[-limit:]]

@app.get("/demo")
async def demo():
    """Run a complete demo scenario"""
    t = Telematics(
        vehicle_id="VHC-DEMO",
        vehicle_model="Tesla Model 3",  # 🆕 Added
        timestamp=datetime.utcnow(),
        mileage_km=58213,
        engine_temp_c=112.5,
        rpm=4200,
        brake_pad_mm=1.4,
        oil_quality_pct=22.0,
        dtc_codes=["P0301"],
    )
    return await ingest_telematics(t)