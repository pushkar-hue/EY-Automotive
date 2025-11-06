# app/agents/mocks.py
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.schemas import (
    Telematics, PredictedIssue, VoiceScript, AppointmentProposal, 
    AppointmentConfirmation, FeedbackPrompt, RCAInsight
)
from app.ueba import UEBA
from app.state import APPOINTMENTS

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google-generativeai not installed. Run: pip install google-generativeai")

from dotenv import load_dotenv
load_dotenv()


class MockDataAgent:
    """Analyze telematics data for anomalies"""
    
    async def analyze(self, t: Telematics) -> Dict[str, Any]:
        UEBA.log("data", "read", "telematics:read", {"vehicle_id": t.vehicle_id})
        
        anomalies = {}
        
        # Detect anomalies
        if t.engine_temp_c > 105:
            anomalies["engine_temp"] = {
                "value": t.engine_temp_c,
                "threshold": 105,
                "severity": "high" if t.engine_temp_c > 110 else "medium"
            }
        
        if t.brake_pad_mm < 3.0:
            anomalies["brake_pad"] = {
                "value": t.brake_pad_mm,
                "threshold": 3.0,
                "severity": "critical" if t.brake_pad_mm < 2.0 else "high"
            }
        
        if t.oil_quality_pct < 30:
            anomalies["oil_quality"] = {
                "value": t.oil_quality_pct,
                "threshold": 30,
                "severity": "high" if t.oil_quality_pct < 20 else "medium"
            }
        
        if t.rpm > 4000:
            anomalies["high_rpm"] = {
                "value": t.rpm,
                "threshold": 4000,
                "severity": "medium"
            }
        
        return {
            "status": "analyzed",
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "overall_health": "poor" if len(anomalies) > 2 else "fair" if len(anomalies) > 0 else "good"
        }


class MockDiagnosisAgent:
    """Predict vehicle failures based on telematics"""
    
    async def predict(self, t: Telematics) -> PredictedIssue:
        UEBA.log("diagnosis", "write", "predictions:write", {"vehicle_id": t.vehicle_id})
        
        # Simple rule-based prediction (replace with your ML model!)
        component = "engine"
        risk_score = 0.3
        horizon_days = 60
        rationale = "Normal operation"
        
        # Engine issues
        if t.engine_temp_c > 110 or t.oil_quality_pct < 20:
            component = "engine"
            risk_score = 0.85
            horizon_days = 7
            rationale = f"High engine temp ({t.engine_temp_c}°C) and low oil quality ({t.oil_quality_pct}%)"
        
        # Brake issues
        elif t.brake_pad_mm < 2.0:
            component = "brakes"
            risk_score = 0.90
            horizon_days = 3
            rationale = f"Critical brake pad wear ({t.brake_pad_mm}mm remaining)"
        
        elif t.brake_pad_mm < 3.0:
            component = "brakes"
            risk_score = 0.65
            horizon_days = 14
            rationale = f"Low brake pad thickness ({t.brake_pad_mm}mm)"
        
        # Oil issues
        elif t.oil_quality_pct < 30:
            component = "oil"
            risk_score = 0.70
            horizon_days = 10
            rationale = f"Poor oil quality ({t.oil_quality_pct}%)"
        
        # Battery (based on DTC codes)
        elif "P0562" in t.dtc_codes:
            component = "battery"
            risk_score = 0.75
            horizon_days = 5
            rationale = "Battery voltage low (DTC P0562)"
        
        return PredictedIssue(
            vehicle_id=t.vehicle_id,
            component=component,
            risk_score=risk_score,
            horizon_days=horizon_days,
            days_to_failure=horizon_days,
            confidence=0.85,
            rationale=rationale
        )


class MockSchedulingAgent:
    """Propose and confirm service appointments"""
    
    async def propose(self, vehicle_id: str) -> AppointmentProposal:
        UEBA.log("scheduling", "read", "slots:read", {"vehicle_id": vehicle_id})
        
        # Generate 3 appointment options
        now = datetime.now()
        options = [
            (now + timedelta(days=1, hours=9)).isoformat(),
            (now + timedelta(days=2, hours=14)).isoformat(),
            (now + timedelta(days=3, hours=10)).isoformat(),
        ]
        
        return AppointmentProposal(
            vehicle_id=vehicle_id,
            options=options,
            center="AutoCare Service Center - Downtown"
        )
    
    async def confirm(self, vehicle_id: str, slot: str) -> AppointmentConfirmation:
        UEBA.log("scheduling", "write", "booking:write", {"vehicle_id": vehicle_id, "slot": slot})
        
        booking_id = f"BK-{vehicle_id}-{random.randint(1000, 9999)}"
        
        confirmation = AppointmentConfirmation(
            vehicle_id=vehicle_id,
            chosen_slot=slot,
            center="AutoCare Service Center - Downtown",
            booking_id=booking_id
        )
        
        # Store in state
        APPOINTMENTS[vehicle_id] = confirmation
        
        return confirmation


class MockManufacturingAgent:
    """Submit RCA insights to manufacturing"""
    
    async def submit_rca(self, insight: RCAInsight) -> bool:
        UEBA.log("mfg", "write", "rca:write", {"title": insight.title})
        
        print("\n" + "="*70)
        print("🏭 MANUFACTURING RCA SUBMISSION")
        print("="*70)
        print(f"📋 Title: {insight.title}")
        print(f"📝 Summary: {insight.summary}")
        print(f"✅ Actions ({len(insight.actions)}):")
        for i, action in enumerate(insight.actions, 1):
            print(f"   {i}. {action}")
        print("="*70 + "\n")
        
        return True


class GeminiVoiceAgent:
    """Voice Agent powered by Gemini Flash 2.0"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key or not GENAI_AVAILABLE:
            print("⚠️  WARNING: GEMINI_API_KEY not set or google-generativeai not installed. Using fallback mode.")
            self.gemini_available = False
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                self.gemini_available = True
                print("✅ Gemini Flash 2.0 initialized successfully")
            except Exception as e:
                print(f"⚠️  Gemini initialization failed: {e}. Using fallback mode.")
                self.gemini_available = False
    
    async def craft_script(self, issue: PredictedIssue, telematics: Optional[Telematics] = None) -> VoiceScript:
        UEBA.log("voice", "read", "issue:read", {"component": issue.component})
        
        if self.gemini_available:
            try:
                script_text = await self._generate_with_gemini(issue, telematics)
            except Exception as e:
                print(f"❌ Gemini generation failed: {e}. Using fallback.")
                script_text = self._fallback_script(issue)
        else:
            script_text = self._fallback_script(issue)
        
        urgency = self._determine_urgency(issue.risk_score)
        
        return VoiceScript(
            vehicle_id=issue.vehicle_id,
            script=script_text,
            urgency=urgency,
            estimated_duration_sec=self._estimate_duration(script_text)
        )
    
    async def _generate_with_gemini(self, issue: PredictedIssue, telematics: Optional[Telematics]) -> str:
        prompt = self._build_gemini_prompt(issue, telematics)
        
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.9,
                top_p=0.95,
                top_k=40,
                max_output_tokens=800,
            )
        )
        
        return response.text.strip()
    
    def _build_gemini_prompt(self, issue: PredictedIssue, telematics: Optional[Telematics]) -> str:
        if issue.risk_score >= 0.8:
            urgency_context = "CRITICAL SAFETY ISSUE - Requires immediate attention"
        elif issue.risk_score >= 0.6:
            urgency_context = "HIGH PRIORITY - Needs prompt attention"
        else:
            urgency_context = "PROACTIVE MAINTENANCE - Prevent future problems"
        
        vehicle_context = ""
        if telematics:
            vehicle_context = f"\n- Model: {telematics.vehicle_model}\n- Mileage: {telematics.mileage_km:,} km"
        
        return f"""You are an automotive service advisor calling a customer.

SITUATION: {urgency_context}

ISSUE:
- Component: {issue.component}
- Risk: {issue.risk_score:.0%}
- Days Until Failure: {issue.days_to_failure}{vehicle_context}

Create a 30-45 second persuasive phone script that:
1. Opens warmly
2. Explains the issue clearly (no jargon)
3. Creates appropriate urgency
4. Highlights benefits of immediate action
5. Ends with clear call-to-action

Use natural conversational tone. Include [pause] for natural breaks.
Generate ONLY the script."""
    
    def _fallback_script(self, issue: PredictedIssue) -> str:
        if issue.risk_score >= 0.8:
            greeting = "Hello, this is your vehicle care team with an urgent safety notification."
            urgency = "critical"
        elif issue.risk_score >= 0.6:
            greeting = "Hi, this is your vehicle care team with an important maintenance alert."
            urgency = "important"
        else:
            greeting = "Hello, this is your vehicle care team with a proactive maintenance update."
            urgency = "preventive"
        
        return f"""{greeting}

Our monitoring system detected that your {issue.component} needs attention. This is a {urgency} issue with approximately {issue.days_to_failure} days before it could become serious.

[pause]

If we don't address this soon, you could face unexpected breakdowns and costly repairs. The good news? We've caught this early.

[pause]

Can we get you scheduled this week? Most {issue.component} services take under an hour."""
    
    def _determine_urgency(self, risk_score: float) -> str:
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        return "low"
    
    def _estimate_duration(self, script: str) -> int:
        words = len(script.split())
        return int((words / 150) * 60)
    
    async def call_owner(self, vehicle_id: str, script: VoiceScript) -> bool:
        UEBA.log("voice", "action", "owner:call", {"vehicle_id": vehicle_id})
        
        print("\n" + "="*70)
        print(f"📞 CALLING VEHICLE OWNER: {vehicle_id}")
        print(f"🎯 URGENCY: {script.urgency.upper()}")
        print("="*70)
        print(f"\n🤖 AGENT SCRIPT:\n{script.script}\n")
        print("="*70 + "\n")
        
        # Simulate customer response based on urgency
        acceptance_rates = {
            "critical": 0.90,
            "high": 0.75,
            "medium": 0.60,
            "low": 0.45
        }
        acceptance_rate = acceptance_rates.get(script.urgency, 0.70)
        accepted = random.random() < acceptance_rate
        
        result_emoji = "✅" if accepted else "❌"
        print(f"{result_emoji} Customer {'ACCEPTED' if accepted else 'DECLINED'}\n")
        
        return accepted


class MockFeedbackAgent:
    """Request and manage customer feedback"""
    
    async def request_feedback(self, booking_id: str, vehicle_id: str) -> dict:
        UEBA.log("feedback", "action", "prompt:create", {
            "booking_id": booking_id,
            "vehicle_id": vehicle_id
        })
        
        return {
            "booking_id": booking_id,
            "vehicle_id": vehicle_id,
            "status": "sent",
            "delivery_method": "sms+email",
            "incentive": "10% discount on next service",
            "timestamp": datetime.now().isoformat()
        }