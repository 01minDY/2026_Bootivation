"""Tests for the distance-only HTTP contract and 30-second scenario."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

import db
import simulator
from distance_ingest import DistanceIngest
from models import DistanceReading


class DistanceContractTests(unittest.TestCase):
    def test_wire_payload_has_exactly_two_fields(self):
        self.assertEqual(
            set(simulator.payload_at(18)),
            {"distance_m", "distance_level"},
        )

    def test_extra_field_is_rejected(self):
        with self.assertRaises(ValidationError):
            DistanceReading.model_validate(
                {
                    "distance_m": 0.82,
                    "distance_level": "DANGER",
                    "temperature_c": 31.4,
                }
            )

    def test_only_three_input_stages_are_allowed(self):
        for level in ("SAFE", "CAUTION", "DANGER"):
            self.assertEqual(
                DistanceReading(
                    distance_m=2.0,
                    distance_level=level,
                ).distance_level,
                level,
            )
        with self.assertRaises(ValidationError):
            DistanceReading(distance_m=2.0, distance_level="OFFLINE")


class DemoScenarioTests(unittest.TestCase):
    def test_demo_is_exactly_thirty_seconds(self):
        self.assertEqual(simulator.DEMO_DURATION_SECONDS, 30.0)
        self.assertEqual(
            simulator.DISTANCE_KEYFRAMES[-1].second,
            simulator.DEMO_DURATION_SECONDS,
        )

    def test_all_three_stages_are_visible(self):
        expected = {
            4: "SAFE",
            10: "CAUTION",
            18: "DANGER",
            23: "CAUTION",
            28: "SAFE",
        }
        for second, level in expected.items():
            with self.subTest(second=second):
                self.assertEqual(
                    simulator.payload_at(second)["distance_level"],
                    level,
                )

    def test_distance_curve_is_continuous_at_keyframes(self):
        for keyframe in simulator.DISTANCE_KEYFRAMES:
            self.assertAlmostEqual(
                simulator.scenario_at(keyframe.second),
                keyframe.distance_m,
                places=6,
            )


class DashboardIntegrationTests(unittest.TestCase):
    def test_server_enrichment_creates_clickable_incident_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            conn = db.get_conn(str(Path(temp_dir) / "demo.db"))
            ingest = DistanceIngest(conn)
            ingest.handle({"distance_m": 4.2, "distance_level": "SAFE"})
            started = ingest.handle(
                {"distance_m": 0.82, "distance_level": "DANGER"}
            )
            ingest.handle({"distance_m": 0.55, "distance_level": "DANGER"})
            ended = ingest.handle(
                {"distance_m": 1.4, "distance_level": "CAUTION"}
            )
            event_id = started["incident"]["event_id"]
            report = db.get_incident_report(conn, event_id)
            conn.close()

        self.assertEqual(started["incident_transition"], "STARTED")
        self.assertEqual(ended["incident_transition"], "ENDED")
        self.assertIsNotNone(report["end_ts"])
        self.assertEqual(report["risk_level"], "DANGER")
        self.assertEqual(report["min_distance_m"], 0.55)
        self.assertEqual(report["environment"]["temperature_c"], 31.4)
        self.assertEqual(report["environment"]["humidity_pct"], 68.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
