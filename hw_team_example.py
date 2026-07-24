"""Copy-ready integration example for the webcam/HW team."""

from __future__ import annotations

from typing import Literal

from distance_sender import send_distance


CONTROL_SERVER = "http://192.168.0.10:8000"
DistanceLevel = Literal["SAFE", "CAUTION", "DANGER"]


def distance_level_for(distance_m: float) -> DistanceLevel:
    if distance_m <= 1.0:
        return "DANGER"
    if distance_m <= 3.0:
        return "CAUTION"
    return "SAFE"


def on_webcam_distance_measured(distance_m: float) -> None:
    distance_level = distance_level_for(distance_m)
    send_distance(
        distance_m=distance_m,
        distance_level=distance_level,
        server=CONTROL_SERVER,
    )


if __name__ == "__main__":
    on_webcam_distance_measured(0.82)
