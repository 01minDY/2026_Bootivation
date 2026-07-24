"""Validated HTTP payload models for the SafeON control server."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def local_now() -> datetime:
    return datetime.now().astimezone()


RiskLevel = Literal["SAFE", "CAUTION", "DANGER", "OFFLINE"]
DistanceLevel = Literal["SAFE", "CAUTION", "DANGER"]
ActionState = Literal["OPEN", "ACK", "CLOSED"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class DistanceReading(BaseModel):
    """The complete field-to-control wire contract: exactly two values."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    distance_m: float = Field(ge=0, le=100)
    distance_level: DistanceLevel


class IncidentActionUpdate(StrictModel):
    action_status: ActionState


class ImprovementActionCreate(StrictModel):
    event_id: str | None = Field(default=None, max_length=40)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    priority: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    assignee: str | None = Field(default=None, max_length=80)
    due_date: str | None = Field(default=None, max_length=10)


class ImprovementActionUpdate(StrictModel):
    status: Literal["OPEN", "IN_PROGRESS", "CLOSED"] | None = None
    assignee: str | None = Field(default=None, max_length=80)
    due_date: str | None = Field(default=None, max_length=10)


class RecommendationApprovalUpdate(StrictModel):
    approved: bool
