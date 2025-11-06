from typing import Dict, List, Any
from app.schemas import AppointmentConfirmation, UEBAEvent, UEBAAlert

# Simple in-memory state stores
VEHICLE_STATE: Dict[str, Dict[str, Any]] = {}
APPOINTMENTS: Dict[str, AppointmentConfirmation] = {}
UEBA_LOG: List[UEBAEvent] = []
UEBA_ALERTS: List[UEBAAlert] = []