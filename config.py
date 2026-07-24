"""SafeON control-server configuration."""

from __future__ import annotations

import os

# Distance stages (metres)
DISTANCE_DANGER_M = 1.0
DISTANCE_CAUTION_M = 3.0

# HTTP distance-source health
PROXIMITY_DEGRADED_SEC = 2.0
PROXIMITY_OFFLINE_SEC = 5.0
ENV_INTERVAL_SEC = 30 * 60
ENV_OFFLINE_MISSES = 2

# Server-generated values. Only distance_m and distance_level arrive over the
# network; these values fill the existing dashboard/report contract.
MOCK_WORKER_ID = "W01"
MOCK_EQUIPMENT_ID = "E01"
MOCK_TEMPERATURE_C = 31.4
MOCK_HUMIDITY_PCT = 68.0
MOCK_WORKER_BATTERY_PCT = 93.0
MOCK_EQUIPMENT_BATTERY_PCT = 89.0

# Incident rules
LONG_EXPOSURE_SEC = 30.0
REPEAT_INCIDENT_COUNT = 3

# Improvement recommendation mock assessment
MOCK_LIKELIHOOD_LABEL = "상"
MOCK_LIKELIHOOD_SCORE = 4
MOCK_SEVERITY_LABEL = "대"
MOCK_SEVERITY_SCORE = 3
MOCK_RISK_GRADE = "상"
MOCK_EQUIPMENT_KIND = "지게차"
MOCK_RECOMMENDATION_DUE_HOURS = 24

# Storage
DB_PATH = os.getenv("SAFEON_DB_PATH", "safeon.db")

RISK_LEVELS = ("SAFE", "CAUTION", "DANGER", "OFFLINE")
RISK_LABELS = {
    "SAFE": "안전",
    "CAUTION": "주의",
    "DANGER": "위험",
    "OFFLINE": "통신장애",
}

HEAT_LEVELS = (
    "NORMAL",
    "HEAT_CAUTION",
    "REST_REQUIRED",
    "STOP_RECOMMENDED",
    "EMERGENCY_STOP",
)
HEAT_LABELS = {
    "NORMAL": "정상",
    "HEAT_CAUTION": "온열 주의",
    "REST_REQUIRED": "휴식 필요",
    "STOP_RECOMMENDED": "작업중지 권고",
    "EMERGENCY_STOP": "긴급 작업중지",
}

ACTION_STATES = ("OPEN", "ACK", "CLOSED")
