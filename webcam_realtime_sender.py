"""YOLO Pose distance estimation and real-time SafeON HTTP transmission."""

from __future__ import annotations

import math
import time

import cv2
import requests
from ultralytics import YOLO


# ---------------------------------------------------------------------------
# Network configuration
# ---------------------------------------------------------------------------

# Use the control laptop C's real IPv4 address when this program runs on A/B.
CONTROL_TOWER_URL = "http://192.168.104.190:8000/api/distance"

ESP32_URLS = (
    "http://192.168.137.166/update",
    "http://192.168.137.223/update",
)


# ---------------------------------------------------------------------------
# Camera / model / transmission configuration
# ---------------------------------------------------------------------------

MODEL_PATH = "yolov8n-pose.pt"
CAMERA_INDEX = 1
PIXEL_TO_METER_RATIO = 0.004
ANKLE_CONFIDENCE_MIN = 0.35
SEND_INTERVAL_SECONDS = 0.2

LEFT_ANKLE_INDEX = 15
RIGHT_ANKLE_INDEX = 16


def distance_level_for(distance_m: float) -> str:
    if distance_m <= 1.0:
        return "DANGER"
    if distance_m <= 3.0:
        return "CAUTION"
    return "SAFE"


def ankle_points(result) -> list[tuple[float, float]]:
    """Return one representative ankle/foot point for each detected person."""
    keypoints = result.keypoints
    if keypoints is None or keypoints.xy is None:
        return []

    xy = keypoints.xy.cpu().numpy()
    confidence = (
        keypoints.conf.cpu().numpy()
        if keypoints.conf is not None
        else None
    )
    points: list[tuple[float, float]] = []

    for person_index, person in enumerate(xy):
        valid_ankles: list[tuple[float, float]] = []

        for ankle_index in (LEFT_ANKLE_INDEX, RIGHT_ANKLE_INDEX):
            if ankle_index >= len(person):
                continue

            x, y = person[ankle_index]
            if x <= 0 or y <= 0:
                continue

            if (
                confidence is not None
                and confidence[person_index][ankle_index]
                < ANKLE_CONFIDENCE_MIN
            ):
                continue

            valid_ankles.append((float(x), float(y)))

        if valid_ankles:
            foot_x = sum(point[0] for point in valid_ankles) / len(valid_ankles)
            foot_y = sum(point[1] for point in valid_ankles) / len(valid_ankles)
            points.append((foot_x, foot_y))

    return points


def closest_pair_distance(
    points: list[tuple[float, float]],
) -> tuple[float | None, tuple[tuple[float, float], tuple[float, float]] | None]:
    """Return closest detected-person distance in metres and the source pair."""
    if len(points) < 2:
        return None, None

    minimum_pixels = math.inf
    closest_pair = None

    for first_index in range(len(points)):
        for second_index in range(first_index + 1, len(points)):
            first = points[first_index]
            second = points[second_index]
            distance_pixels = math.hypot(
                first[0] - second[0],
                first[1] - second[1],
            )
            if distance_pixels < minimum_pixels:
                minimum_pixels = distance_pixels
                closest_pair = (first, second)

    return float(minimum_pixels * PIXEL_TO_METER_RATIO), closest_pair


def send_to_control_tower(
    session: requests.Session,
    distance_m: float,
    distance_level: str,
) -> None:
    """Send the exact two-field SafeON packet to control laptop C."""
    payload = {
        "distance_m": round(distance_m, 2),
        "distance_level": distance_level,
    }
    response = session.post(
        CONTROL_TOWER_URL,
        json=payload,
        timeout=1.0,
    )
    response.raise_for_status()


def send_to_esp32(
    session: requests.Session,
    distance_m: float,
    distance_level: str,
) -> None:
    params = {
        "distance": round(distance_m, 2),
        "status": distance_level,
    }
    for url in ESP32_URLS:
        response = session.get(url, params=params, timeout=0.5)
        response.raise_for_status()


def annotate_distance(
    frame,
    pair: tuple[tuple[float, float], tuple[float, float]] | None,
    distance_m: float | None,
    distance_level: str | None,
) -> None:
    if pair is None or distance_m is None or distance_level is None:
        cv2.putText(
            frame,
            "WAITING FOR 2 VALID PEOPLE",
            (24, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 190, 255),
            2,
        )
        return

    first = (int(pair[0][0]), int(pair[0][1]))
    second = (int(pair[1][0]), int(pair[1][1]))
    color = {
        "SAFE": (0, 190, 0),
        "CAUTION": (0, 210, 255),
        "DANGER": (0, 0, 255),
    }[distance_level]

    cv2.circle(frame, first, 7, color, -1)
    cv2.circle(frame, second, 7, color, -1)
    cv2.line(frame, first, second, color, 3)
    cv2.putText(
        frame,
        f"{distance_m:.2f}m / {distance_level}",
        (24, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        color,
        2,
    )


def main() -> int:
    model = YOLO(MODEL_PATH)
    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        raise RuntimeError(
            f"카메라 {CAMERA_INDEX}을 열 수 없습니다. "
            "CAMERA_INDEX를 0 또는 1로 변경하세요."
        )

    session = requests.Session()
    last_send_at = 0.0
    last_error_at = 0.0
    last_console_at = 0.0
    previous_level = None

    try:
        while camera.isOpened():
            success, frame = camera.read()
            if not success:
                break

            result = model(frame, verbose=False)[0]
            annotated_frame = result.plot()

            points = ankle_points(result)
            distance_m, closest_pair = closest_pair_distance(points)
            distance_level = (
                distance_level_for(distance_m)
                if distance_m is not None
                else None
            )

            annotate_distance(
                annotated_frame,
                closest_pair,
                distance_m,
                distance_level,
            )

            current_time = time.monotonic()
            transmission_due = (
                distance_m is not None
                and distance_level is not None
                and current_time - last_send_at >= SEND_INTERVAL_SECONDS
            )

            if transmission_due:
                try:
                    send_to_control_tower(
                        session,
                        distance_m,
                        distance_level,
                    )
                    send_to_esp32(
                        session,
                        distance_m,
                        distance_level,
                    )

                    if (
                        distance_level != previous_level
                        or current_time - last_console_at >= 1.0
                    ):
                        print(
                            "[전송 성공] "
                            f"{distance_m:.2f}m / {distance_level}"
                        )
                        last_console_at = current_time
                        previous_level = distance_level

                except requests.exceptions.RequestException as error:
                    if current_time - last_error_at >= 2.0:
                        print(f"[HTTP 전송 실패] {error}")
                        last_error_at = current_time

                last_send_at = current_time

            cv2.imshow("SafeON Monitoring System", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        session.close()
        camera.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
