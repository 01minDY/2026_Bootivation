"""Two-field HTTP distance ingestion with server-side mock enrichment."""

from __future__ import annotations

from datetime import datetime
from threading import Lock

import config
import db
import risk_engine
from models import DistanceReading


class DistanceIngest:
    """Accept distance + stage, then create the existing dashboard data shape."""

    def __init__(self, conn, on_update=None):
        self.conn = conn
        self.on_update = on_update or (lambda payload: None)
        self.latest: dict | None = None
        self.environment = self._mock_environment()
        self._sequence = 0
        self._lock = Lock()
        self.stats = {
            "received": 0,
            "accepted": 0,
            "incidents_started": 0,
            "last_received": None,
        }
        db.record_environment(self.conn, self.environment, transport="mock")

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="milliseconds")

    def _mock_environment(self) -> dict:
        timestamp = self._now()
        apparent = risk_engine.apparent_temperature(
            config.MOCK_TEMPERATURE_C,
            config.MOCK_HUMIDITY_PCT,
        )
        heat_level = risk_engine.heat_level_for(apparent)
        guidance = risk_engine.heat_guidance(heat_level)
        return {
            "timestamp": timestamp,
            "equipment_id": config.MOCK_EQUIPMENT_ID,
            "temperature_c": config.MOCK_TEMPERATURE_C,
            "humidity_pct": config.MOCK_HUMIDITY_PCT,
            "apparent_temperature_c": apparent,
            "heat_level": heat_level,
            "heat_label": config.HEAT_LABELS[heat_level],
            "sensor_status": "NORMAL",
            "guidance": guidance["message"],
            "legal_basis": guidance["legal_basis"],
            "worker_alert": guidance,
        }

    def handle(self, reading: DistanceReading | dict) -> dict:
        """Persist and publish one strictly validated two-field reading."""
        self.stats["received"] += 1
        model = (
            reading
            if isinstance(reading, DistanceReading)
            else DistanceReading.model_validate(reading)
        )
        timestamp = self._now()
        with self._lock:
            self._sequence += 1
            sequence = self._sequence

        received_level = model.distance_level
        level = risk_engine.risk_level_for_distance(model.distance_m)
        item = {
            "timestamp": timestamp,
            "worker_id": config.MOCK_WORKER_ID,
            "equipment_id": config.MOCK_EQUIPMENT_ID,
            "distance_m": round(float(model.distance_m), 3),
            "risk_level": level,
            "received_distance_level": received_level,
            "risk_label": config.RISK_LABELS[level],
            "near_miss": level == "DANGER",
            "sequence": sequence,
            "battery_pct": config.MOCK_WORKER_BATTERY_PCT,
            "equipment_battery_pct": config.MOCK_EQUIPMENT_BATTERY_PCT,
            "sensor_error_code": None,
            "firmware_version": "HTTP-DISTANCE-1.0",
            "alert": risk_engine.proximity_alert(level, model.distance_m),
            "risk_mismatch": received_level != level,
        }
        incident = db.record_proximity(self.conn, item, transport="http")
        item["incident_transition"] = incident["transition"]
        item["incident"] = incident["incident"]
        self.latest = item
        self.stats["accepted"] += 1
        self.stats["last_received"] = timestamp
        if incident["transition"] == "STARTED":
            self.stats["incidents_started"] += 1
        self.on_update({"type": "proximity", **item})
        return {"accepted": True, **item}
