"""Real-time 30-second SafeON distance-only demonstration."""

from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass

import risk_engine
from distance_sender import DistanceSendError, check_server, send_distance


DEMO_DURATION_SECONDS = 30.0


@dataclass(frozen=True)
class DistanceKeyframe:
    second: float
    distance_m: float


# Smooth approach and retreat with clear dwell time in all three stages.
DISTANCE_KEYFRAMES = (
    DistanceKeyframe(0.0, 4.80),
    DistanceKeyframe(4.0, 4.30),
    DistanceKeyframe(7.0, 3.20),
    DistanceKeyframe(8.0, 2.80),
    DistanceKeyframe(12.0, 2.00),
    DistanceKeyframe(15.0, 1.15),
    DistanceKeyframe(16.0, 0.92),
    DistanceKeyframe(19.0, 0.58),
    DistanceKeyframe(21.0, 0.78),
    DistanceKeyframe(22.0, 1.25),
    DistanceKeyframe(25.0, 2.75),
    DistanceKeyframe(26.0, 3.25),
    DistanceKeyframe(30.0, 4.60),
)

STAGE_KO = {
    "SAFE": "안전",
    "CAUTION": "주의",
    "DANGER": "위험",
}


def _smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def scenario_at(elapsed: float) -> float:
    """Return a continuous, physically plausible distance in metres."""
    elapsed = max(0.0, min(DEMO_DURATION_SECONDS, float(elapsed)))
    for start, end in zip(DISTANCE_KEYFRAMES, DISTANCE_KEYFRAMES[1:]):
        if start.second <= elapsed <= end.second:
            progress = (elapsed - start.second) / (end.second - start.second)
            eased = _smoothstep(progress)
            return start.distance_m + (end.distance_m - start.distance_m) * eased
    return DISTANCE_KEYFRAMES[-1].distance_m


def payload_at(elapsed: float, noise_m: float = 0.0) -> dict:
    """Build the complete wire payload; it always has exactly two keys."""
    distance = scenario_at(elapsed) + noise_m
    distance = round(max(0.0, distance), 2)
    return {
        "distance_m": distance,
        "distance_level": risk_engine.risk_level_for_distance(distance),
    }


def run_demo(server: str, interval: float, noise: bool, seed: int) -> str | None:
    health = check_server(server)
    fields = health.get("input_fields", [])
    if fields != ["distance_m", "distance_level"]:
        raise DistanceSendError("서버의 거리 수신 계약이 예상과 다릅니다.")

    started = time.monotonic()
    next_tick = started
    previous_level = None
    event_id = None
    randomizer = random.Random(seed)

    print("SafeON 30초 시연 시작")
    print("안전 → 주의 → 위험(사건 생성) → 주의 → 안전")
    print("송신 필드: distance_m, distance_level")
    print("-" * 62)

    while True:
        elapsed = time.monotonic() - started
        if elapsed >= DEMO_DURATION_SECONDS:
            break

        jitter = randomizer.uniform(-0.025, 0.025) if noise else 0.0
        payload = payload_at(elapsed, jitter)
        result = send_distance(
            payload["distance_m"],
            payload["distance_level"],
            server=server,
        )
        level = payload["distance_level"]
        incident = result.get("incident") or {}
        event_id = incident.get("event_id") or event_id

        if level != previous_level:
            print(
                f"\n[{elapsed:05.1f}초] 단계 전환 → "
                f"{STAGE_KO[level]} ({level})"
            )
        transition = result.get("incident_transition")
        if transition == "STARTED":
            print(f"          사건 생성 → {event_id}")
        elif transition == "ENDED":
            print(f"          사건 종료 → {event_id}")
        print(
            f"  {elapsed:05.1f}초 | {payload['distance_m']:>4.2f}m | "
            f"{STAGE_KO[level]:<4}",
            flush=True,
        )
        previous_level = level
        next_tick += interval
        remaining = next_tick - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)

    print("-" * 62)
    print("30초 시연 완료 · 안전거리 복귀")
    if event_id:
        print(f"대시보드에서 {event_id}를 눌러 개별사건 리포트를 확인하세요.")
    return event_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="거리값과 거리단계만 HTTP로 보내는 SafeON 30초 시뮬레이터"
    )
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--noise", action="store_true", help="±2.5cm 미세 변동")
    parser.add_argument("--seed", type=int, default=20260725)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval은 0보다 커야 합니다.")
    try:
        run_demo(args.server, args.interval, args.noise, args.seed)
    except KeyboardInterrupt:
        print("\n시뮬레이터 종료")
        return 130
    except DistanceSendError as exc:
        print(f"\n[실행 실패] {exc}")
        print("먼저 관제 노트북에서 uvicorn main:app --host 0.0.0.0 --port 8000")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
