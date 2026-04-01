from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


CategoryName = Literal[
    "planning",
    "debugging",
    "constraints",
    "iteration",
    "correction",
    "tool_usage",
    "repetition",
]


class CategoryResult(BaseModel):
    score: int = Field(ge=1, le=5)
    reasoning: str
    evidence: list[str]
    confidence: float = Field(ge=0, le=1)


class EvaluationResponse(BaseModel):
    overall_score: float = Field(ge=1, le=5)
    label: Literal["Poor", "Average", "Good", "Strong"]
    categories: dict[CategoryName, CategoryResult]
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    summary: str
    reflection: str
    transcript_format: str
    phase_timeline: list[dict[str, Any]]
    parsed_messages: int


class EvaluateRequest(BaseModel):
    transcript_text: str | None = None
    transcript_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompareSessionInput(BaseModel):
    name: str
    transcript_text: str | None = None
    transcript_path: str | None = None


class CompareRequest(BaseModel):
    sessions: list[CompareSessionInput] = Field(min_length=2)
