import time
from typing import Dict, List, Any
from app.schemas import UEBAEvent, UEBAAlert
from app.state import UEBA_LOG, UEBA_ALERTS

class UEBAGuard:
    """Lightweight UEBA: allow-lists and simple anomaly heuristics."""
    
    # Which resources each agent is allowed to touch
    ALLOW: Dict[str, List[str]] = {
        "data": ["telematics:read"],
        "diagnosis": ["telematics:read", "predictions:write"],
        "voice": ["owner:contact", "summary:read"],
        "scheduling": ["slots:read", "booking:write"],
        "feedback": ["owner:contact", "feedback:write"],
        "mfg": ["rca:write", "history:read"],
        "master": [
            "telematics:read", "predictions:read", "owner:contact",
            "slots:read", "booking:write", "feedback:write", "rca:write",
        ],
    }

    # Simple rate baseline: actor -> last N actions timestamps (per resource)
    def __init__(self):
        self.window: Dict[str, List[float]] = {}

    def log(self, actor: str, action: str, resource: str, details: Dict[str, Any] | None = None):
        ts = time.time()
        ev = UEBAEvent(ts=ts, actor=actor, action=action, resource=resource, details=details or {})
        UEBA_LOG.append(ev)

        # Allow-list check
        if resource not in self.ALLOW.get(actor, []):
            UEBA_ALERTS.append(
                UEBAAlert(ts=ts, severity="high", actor=actor, reason=f"Unauthorized resource: {resource}", event=ev)
            )

        # Simple spike detection: if > 5 actions in 3 seconds → alert
        key = f"{actor}:{resource}"
        arr = self.window.setdefault(key, [])
        arr.append(ts)
        # keep last 10 timestamps
        if len(arr) > 10:
            self.window[key] = arr[-10:]
        arr = self.window[key]
        recent = [x for x in arr if ts - x <= 3.0]
        if len(recent) > 5:
            UEBA_ALERTS.append(
                UEBAAlert(ts=ts, severity="medium", actor=actor, reason="Spike in actions", event=ev)
            )

# Create a single, shared instance for the whole app
UEBA = UEBAGuard()