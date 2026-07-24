"""Small dependency-free sender for the webcam distance program."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Literal, TypedDict


DISTANCE_LEVELS = ("SAFE", "CAUTION", "DANGER")
DistanceLevel = Literal["SAFE", "CAUTION", "DANGER"]


class DistancePacket(TypedDict):
    distance_m: float
    distance_level: DistanceLevel


class DistanceSendError(RuntimeError):
    pass


def _request(server: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{server.rstrip('/')}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DistanceSendError(f"HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DistanceSendError(f"관제 서버 연결 실패: {exc}") from exc


def check_server(server: str = "http://127.0.0.1:8000") -> dict:
    return _request(server, "/api/health")


def build_packet(distance_m: float, distance_level: str) -> DistancePacket:
    level = str(distance_level).strip().upper()
    if level not in DISTANCE_LEVELS:
        raise ValueError(f"distance_level은 {DISTANCE_LEVELS} 중 하나여야 합니다.")
    return {
        "distance_m": float(distance_m),
        "distance_level": level,
    }


def send_distance(
    distance_m: float,
    distance_level: str,
    *,
    server: str = "http://127.0.0.1:8000",
) -> dict:
    """Send exactly the two values accepted by the control server."""
    return _request(
        server,
        "/api/distance",
        build_packet(distance_m, distance_level),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="SafeON 거리 1건 HTTP 전송")
    parser.add_argument("distance_m", type=float)
    parser.add_argument("distance_level", choices=DISTANCE_LEVELS)
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        result = send_distance(
            args.distance_m,
            args.distance_level,
            server=args.server,
        )
    except (DistanceSendError, ValueError) as exc:
        print(f"전송 실패: {exc}")
        return 1
    print(
        f"전송 완료: {result['distance_m']:.2f}m "
        f"{result['risk_level']} · SEQ {result['sequence']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
