import os
import random
from typing import Dict, Any, Optional
from app.schemas import (
    Telematics, PredictedIssue, VoiceScript, AppointmentProposal, 
    AppointmentConfirmation, FeedbackPrompt, RCAInsight
)
from app.ueba import UEBA
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()
class MockDataAgent:
    async def analyze(self, t: Telematics) -> Dict[str, Any]:
        return {"status": "success", "data": {"issue": "mocked_issue"}}

class MockDiagnosisAgent:
    async def predict(self, t: Telematics) -> PredictedIssue:
        return {"status": "success", "data": {"issue": "mocked_issue"}}


class MockSchedulingAgent:
    async def propose(self, vehicle_id: str) -> AppointmentProposal:
        return {"status": "success", "data": {"appointment": "mocked_appointment"}}
    async def confirm(self, vehicle_id: str, slot: str) -> AppointmentConfirmation:
        return {"status": "success", "data": {"confirmation": "mocked_confirmation"}}

class MockManufacturingAgent:
    async def submit_rca(self, insight: RCAInsight) -> bool:
        return {"status": "success"}


class GeminiVoiceAgent:
    """
    Voice Agent powered by Gemini Flash 2.0 for highly persuasive,
    contextual, and engaging customer conversations
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini API
        
        Args:
            api_key: Gemini API key (or set GEMINI_API_KEY env variable)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            print("⚠️  WARNING: GEMINI_API_KEY not set. Using fallback mode.")
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
        """
        Craft highly persuasive voice script using Gemini Flash 2.0
        
        Args:
            issue: Predicted vehicle issue
            telematics: Optional vehicle telematics data for context
        """
        UEBA.log("voice", "read", "issue:read", {"component": issue.component})
        
        if self.gemini_available:
            try:
                script_text = await self._generate_with_gemini(issue, telematics)
                urgency = self._determine_urgency(issue.risk_score)
            except Exception as e:
                print(f"❌ Gemini generation failed: {e}. Using fallback.")
                script_text = self._fallback_script(issue)
                urgency = self._determine_urgency(issue.risk_score)
        else:
            script_text = self._fallback_script(issue)
            urgency = self._determine_urgency(issue.risk_score)
        
        return VoiceScript(
            vehicle_id="",
            script=script_text,
            urgency=urgency,
            estimated_duration_sec=self._estimate_duration(script_text)
        )
    
    async def _generate_with_gemini(
        self, 
        issue: PredictedIssue, 
        telematics: Optional[Telematics]
    ) -> str:
        """
        Generate persuasive script using Gemini Flash 2.0
        """
        # Build context-rich prompt
        prompt = self._build_gemini_prompt(issue, telematics)
        
        # Generate with specific parameters for conversational tone
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.9,  # More creative for engaging scripts
                top_p=0.95,
                top_k=40,
                max_output_tokens=800,
            )
        )
        
        script = response.text.strip()
        
        UEBA.log("voice", "action", "gemini:generate", {
            "component": issue.component,
            "risk_score": issue.risk_score,
            "script_length": len(script)
        })
        
        return script
    
    def _build_gemini_prompt(
        self, 
        issue: PredictedIssue, 
        telematics: Optional[Telematics]
    ) -> str:
        """
        Build a detailed prompt for Gemini to generate persuasive scripts
        """
        # Determine urgency level
        if issue.risk_score >= 0.8:
            urgency_context = "CRITICAL SAFETY ISSUE - This requires immediate attention to prevent dangerous situations."
        elif issue.risk_score >= 0.6:
            urgency_context = "HIGH PRIORITY - This needs prompt attention to avoid costly repairs and inconvenience."
        else:
            urgency_context = "PROACTIVE MAINTENANCE - Addressing this now prevents future problems."
        
        # Add vehicle context if available
        vehicle_context = ""
        if telematics:
            vehicle_context = f"""
Vehicle Context:
- Model: {telematics.vehicle_model}
- Mileage: {telematics.mileage_km:,} km
- Last Service: Recent monitoring detected this issue
"""
        
        prompt = f"""You are an expert automotive service advisor making an important phone call to a vehicle owner. Your goal is to persuade them to schedule maintenance while being empathetic, clear, and professional.

SITUATION:
{urgency_context}

VEHICLE ISSUE DETAILS:
- Component: {issue.component}
- Risk Score: {issue.risk_score:.1%} probability of failure
- Estimated Days Until Failure: {issue.days_to_failure} days
- Confidence: {issue.confidence:.1%}
{vehicle_context}

YOUR TASK:
Create a persuasive phone script (30-45 seconds spoken) that:

1. **Opens warmly** - Use a friendly greeting that doesn't alarm them immediately
2. **Builds credibility** - Mention advanced diagnostics/monitoring system
3. **Explains the issue clearly** - Use simple terms, avoid jargon
4. **Creates urgency (without panic)** - Explain consequences of not acting
5. **Highlights benefits** - Focus on safety, cost savings, peace of mind
6. **Uses social proof** - Reference that "many customers" or "in our experience"
7. **Makes it easy** - Mention convenient scheduling, quick service time
8. **Ends with clear call-to-action** - Direct question asking if they can schedule

TONE GUIDELINES:
- Conversational and natural (like a real phone call)
- Empathetic and understanding
- Confident but not pushy
- Use "we" and "you" language
- Include natural pauses with [pause]
- Add a moment for customer response with [wait for response]

AVOID:
- Technical jargon
- Being too aggressive or salesy
- Downplaying the issue
- Being too wordy (keep it concise)

Generate ONLY the phone script, no additional commentary.
"""
        
        return prompt
    
    def _fallback_script(self, issue: PredictedIssue) -> str:
        """
        Fallback script when Gemini is unavailable
        """
        if issue.risk_score >= 0.8:
            greeting = "Hello, this is your vehicle care team with an urgent safety notification."
            urgency = "critical safety"
        elif issue.risk_score >= 0.6:
            greeting = "Hi, this is your vehicle care team reaching out about an important maintenance alert."
            urgency = "important maintenance"
        else:
            greeting = "Hello, this is your vehicle care team with a proactive maintenance update."
            urgency = "preventive maintenance"
        
        script = f"""{greeting}

Our advanced monitoring system has detected that your {issue.component} needs attention. This is a {urgency} issue with approximately {issue.days_to_failure} days before it could become a serious problem.

Here's what this means for you: [pause] If we don't address this soon, you could face unexpected breakdowns, safety concerns, and repairs that cost significantly more than preventive maintenance.

The good news? [pause] We've caught this early. A quick service appointment now can save you time, money, and stress down the road.

We have convenient appointment slots available this week, and most {issue.component} services take less than an hour. 

[wait for response]

Can we get you scheduled to take care of this? I have some great time slots available."""
        
        return script
    
    def _determine_urgency(self, risk_score: float) -> str:
        """Determine urgency level from risk score"""
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _estimate_duration(self, script: str) -> int:
        """Estimate speaking duration in seconds (rough: 150 words per minute)"""
        words = len(script.split())
        duration = (words / 150) * 60  # Convert to seconds
        return int(duration)
    
    async def call_owner(self, vehicle_id: str, script: VoiceScript) -> bool:
        """
        Execute the call with optional real voice integration
        
        Options:
        1. Simulated (current) - for testing
        2. Real voice (pyttsx3 + speech recognition) - for demos
        3. Gemini Live API - for production (future enhancement)
        """
        UEBA.log("voice", "action", "owner:call", {"vehicle_id": vehicle_id})
        
        print("\n" + "="*70)
        print(f"📞 CALLING VEHICLE OWNER: {vehicle_id}")
        print(f"🎯 URGENCY: {script.urgency.upper()}")
        print("="*70)
        print(f"\n🤖 AGENT SCRIPT:\n{script.script}\n")
        print("="*70 + "\n")
        
        # ====================================================================
        # OPTION 1: Smart Simulation (risk-based acceptance)
        # ====================================================================
        acceptance_rate = self._calculate_acceptance_rate(script)
        accepted = random.random() < acceptance_rate
        
        # ====================================================================
        # OPTION 2: Real voice call (uncomment to enable)
        # ====================================================================
        # try:
        #     accepted = await self._real_voice_call(vehicle_id, script)
        # except Exception as e:
        #     print(f"❌ Voice call failed: {e}. Using simulation.")
        #     accepted = random.random() < acceptance_rate
        
        # Log result
        result_emoji = "✅" if accepted else "❌"
        print(f"{result_emoji} Customer {'ACCEPTED' if accepted else 'DECLINED'} appointment\n")
        
        UEBA.log("voice", "action", "call:result", {
            "vehicle_id": vehicle_id,
            "accepted": accepted,
            "urgency": script.urgency
        })
        
        return accepted
    
    def _calculate_acceptance_rate(self, script: VoiceScript) -> float:
        """
        Calculate acceptance rate based on script quality and urgency
        """
        base_rates = {
            "critical": 0.90,
            "high": 0.75,
            "medium": 0.60,
            "low": 0.45
        }
        
        base_rate = base_rates.get(script.urgency, 0.70)
        
        # Bonus for Gemini-generated scripts (assumed higher quality)
        if self.gemini_available and len(script.script) > 200:
            base_rate += 0.05
        
        return min(base_rate, 0.95)  # Cap at 95%
    
    async def _real_voice_call(self, vehicle_id: str, script: VoiceScript) -> bool:
        """
        Real voice interaction using TTS and speech recognition
        
        Install: pip install pyttsx3 SpeechRecognition pyaudio
        """
        try:
            import pyttsx3
            import speech_recognition as sr
        except ImportError:
            print("⚠️  Voice libraries not installed. Run: pip install pyttsx3 SpeechRecognition pyaudio")
            return False
        
        # Initialize TTS engine
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)  # Natural speaking pace
        engine.setProperty('volume', 0.9)
        
        # Clean script for speech (remove stage directions)
        clean_script = script.script.replace("[pause]", "... ")
        clean_script = clean_script.replace("[wait for response]", "")
        
        # Speak the script
        print("🔊 Speaking to customer...\n")
        engine.say(clean_script)
        engine.runAndWait()
        
        # Listen for response
        print("🎤 Listening for customer response...")
        print("   (Say 'yes', 'okay', 'sure' to accept, or 'no', 'not now' to decline)\n")
        
        recognizer = sr.Recognizer()
        
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
            
            response = recognizer.recognize_google(audio).lower()
            print(f"👤 CUSTOMER SAID: '{response}'\n")
            
            # Analyze response
            positive = ["yes", "yeah", "okay", "ok", "sure", "fine", "alright", "schedule", "book"]
            negative = ["no", "not", "nah", "maybe", "later", "busy", "can't"]
            
            if any(word in response for word in positive):
                return True
            elif any(word in response for word in negative):
                return False
            else:
                print("❓ Response unclear, treating as declined\n")
                return False
                
        except sr.WaitTimeoutError:
            print("⏱️  No response detected (timeout)\n")
            return False
        except sr.UnknownValueError:
            print("🔇 Could not understand audio\n")
            return False
        except Exception as e:
            print(f"❌ Error: {e}\n")
            return False


class MockFeedbackAgent:
    """
    Enhanced Feedback Agent with intelligent collection and analysis
    """
    
    async def request_feedback(self, booking_id: str, vehicle_id: str) -> dict:
        """
        Request customer feedback after service
        """
        UEBA.log("feedback", "action", "prompt:create", {
            "booking_id": booking_id,
            "vehicle_id": vehicle_id
        })
        
        questions = self._generate_questions()
        
        return {
            "booking_id": booking_id,
            "vehicle_id": vehicle_id,
            "prompt_text": self._create_message(questions),
            "questions": questions,
            "delivery_method": "sms+email",
            "incentive": "10% discount on next service",
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_questions(self) -> list:
        """Generate smart feedback questions"""
        return [
            {
                "id": "q1",
                "question": "How would you rate your overall service experience?",
                "type": "rating",
                "scale": "1-5 stars",
                "required": True
            },
            {
                "id": "q2",
                "question": "Was the issue with your vehicle fully resolved?",
                "type": "yes_no",
                "required": True
            },
            {
                "id": "q3",
                "question": "How satisfied are you with the communication throughout the process?",
                "type": "rating",
                "scale": "1-5 stars",
                "required": True
            },
            {
                "id": "q4",
                "question": "What did we do well?",
                "type": "text",
                "required": False
            },
            {
                "id": "q5",
                "question": "How can we improve?",
                "type": "text",
                "required": False
            },
            {
                "id": "q6",
                "question": "Would you recommend our service?",
                "type": "yes_no",
                "required": False
            }
        ]
    
    def _create_message(self, questions: list) -> str:
        """Create engaging feedback request"""
        return f"""
                Thank you for trusting us with your vehicle maintenance! 🚗

                We hope everything went smoothly with your recent service appointment. 
                Your feedback helps us improve and serve you better.

                Complete our quick 2-minute survey and get 10% off your next service!

                We'll ask about:
                1. Overall experience rating
                2. Issue resolution
                3. Communication satisfaction
                ... and a few more questions to help us serve you better.

                Click here to start: [SURVEY_LINK]

                Thank you! 🙏
                Your Vehicle Care Team
                        """.strip()