from fastapi import FastAPI, HTTPException
from datetime import datetime

from app.config import USE_MOCKS
from app.schemas import Telematics
from app.state import VEHICLE_STATE, APPOINTMENTS, UEBA_LOG, UEBA_ALERTS
from app.orchestrator import MasterAgent

# Import specific agents based on config
if USE_MOCKS:
    from app.agents.mocks import (
        MockDataAgent, MockDiagnosisAgent, MockVoiceAgent,
        MockSchedulingAgent, MockFeedbackAgent, MockManufacturingAgent
    )
else:
    # This is where you would import your HTTP-based clients
    raise RuntimeError("HTTP worker clients not wired in this demo – set USE_MOCKS=True.")

# --- App Creation & Dependency Injection ---

app = FastAPI(title="Master Orchestrator – Predictive Maintenance", version="1.0")

# Instantiate Master with either MOCK or HTTP clients
if USE_MOCKS:
    master = MasterAgent(
        data_agent=MockDataAgent(),
        diagnosis_agent=MockDiagnosisAgent(),
        voice_agent=MockVoiceAgent(),
        scheduling_agent=MockSchedulingAgent(),
        feedback_agent=MockFeedbackAgent(),
        mfg_agent=MockManufacturingAgent(),
    )
else:
    # master = MasterAgent(
    #     data_agent=HTTPDataAgent(WORKER_URLS["data"]),
    #     ...
    # )
    pass

# --- API Routes ---

@app.get("/")
async def root():
    return {"ok": True, "service": app.title, "docs": "/docs"}

@app.post("/ingest/telematics")
async def ingest_telematics(t: Telematics):
    """Main entrypoint: send a single telematics sample to drive the full flow."""
    try:
        result = await master.process_telematics(t)
        return {"status": "processed", "result": result, "ueba_alerts": [a.model_dump() for a in UEBA_ALERTS[-5:]]}
    except Exception as e:
        # Log the exception e
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
    return appt

@app.get("/ueba/logs")
async def ueba_logs(limit: int = 100):
    return [e.model_dump() for e in UEBA_LOG[-limit:]]

@app.get("/ueba/alerts")
async def ueba_alerts(limit: int = 50):
    return [a.model_dump() for a in UEBA_ALERTS[-limit:]]

@app.get("/demo")
async def demo():
    t = Telematics(
        vehicle_id="VHC-DEMO",
        timestamp=datetime.utcnow(),
        mileage_km=58213,
        engine_temp_c=112.5,
        rpm=4200,
        brake_pad_mm=1.4,
        oil_quality_pct=22.0,
        dtc_codes=["P0301"],
    )
    return await ingest_telematics(t)