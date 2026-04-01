from __future__ import annotations

import json
from statistics import mean
from typing import Any

from backend.categories import CATEGORY_SPECS
from backend.config import Settings
from backend.parser import Message, detect_transcript_format, transcript_to_chunk
from backend.schemas import CategoryResult, EvaluationResponse


def _label_from_score(score: float) -> str:
    if score < 2.5:
        return "Poor"
    if score < 3.5:
        return "Average"
    if score < 4.5:
        return "Good"
    return "Strong"


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _mock_category_eval(category_name: str, transcript_chunk: str) -> CategoryResult:
    lowered = transcript_chunk.lower()
    hints = {
        "planning": ["plan", "steps", "roadmap", "approach"],
        "debugging": ["error", "stack trace", "debug", "reproduce"],
        "constraints": ["requirement", "constraint", "must", "edge case"],
        "iteration": ["iterate", "refine", "improve", "next version"],
        "correction": ["fix", "correct", "mistake", "wrong"],
        "tool_usage": ["tool", "terminal", "test", "run"],
        "repetition": ["again", "repeat", "same"],
    }

    hit_count = sum(1 for token in hints[category_name] if token in lowered)
    score = max(1, min(5, 2 + hit_count))
    confidence = min(0.95, 0.45 + 0.1 * hit_count)
    return CategoryResult(
        score=score,
        reasoning=f"Mock heuristic evaluation for {category_name} based on keyword density.",
        evidence=[f"Detected {hit_count} category-related signals in transcript chunk."],
        confidence=confidence,
    )


def _evaluate_with_openai(prompt: str, settings: Settings) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.model_name,
        input=prompt,
        temperature=0.1,
    )
    return _extract_json(response.output_text)


def evaluate_category(messages: list[Message], category: dict[str, Any], settings: Settings) -> CategoryResult:
    transcript_chunk = transcript_to_chunk(messages, settings.max_chunk_chars)

    if settings.llm_provider == "mock" or not settings.openai_api_key:
        return _mock_category_eval(category["name"], transcript_chunk)

    prompt = f"""
You are an expert engineering workflow evaluator.

Category: {category["name"]}
Description: {category["description"]}
Positive signals: {category["positive_signals"]}
Negative signals: {category["negative_signals"]}

Transcript chunk:
{transcript_chunk}

Return strict JSON:
{{
  "score": 1-5,
  "reasoning": "short explanation",
  "evidence": ["short quote or behavior"],
  "confidence": 0-1
}}
"""
    result = _evaluate_with_openai(prompt, settings)
    return CategoryResult(**result)


def generate_insights(category_results: dict[str, CategoryResult]) -> tuple[list[str], list[str], list[str], str]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []

    for name, result in category_results.items():
        if result.score >= 4:
            strengths.append(f"{name.replace('_', ' ').title()}: {result.reasoning}")
        if result.score <= 2:
            weaknesses.append(f"{name.replace('_', ' ').title()}: {result.reasoning}")
            suggestions.append(f"Improve {name.replace('_', ' ')} with more explicit, hypothesis-driven prompts.")

    if not strengths:
        strengths.append("Session shows some productive behaviors, but none are consistently strong yet.")
    if not weaknesses:
        weaknesses.append("No critical weaknesses were detected across the evaluated dimensions.")
    if not suggestions:
        suggestions.append("Maintain current process and add explicit verification steps after each major change.")

    summary = (
        "The session balances planning and execution with varying quality across dimensions. "
        "Use strengths as stable habits and convert weak areas into explicit workflow checkpoints."
    )
    return strengths, weaknesses, suggestions, summary


def _detect_phase(message: Message) -> str:
    text = message.content.lower()
    if any(k in text for k in ["plan", "approach", "roadmap", "steps"]):
        return "planning"
    if any(k in text for k in ["implement", "build", "write", "create", "add"]):
        return "implementation"
    if any(k in text for k in ["debug", "error", "trace", "fix", "broken", "issue"]):
        return "debugging"
    if any(k in text for k in ["test", "verify", "validate", "check"]):
        return "validation"
    return "iteration"


def build_phase_timeline(messages: list[Message]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    if not messages:
        return timeline
    current_phase = _detect_phase(messages[0])
    start_index = 0

    for idx, message in enumerate(messages[1:], start=1):
        phase = _detect_phase(message)
        if phase != current_phase:
            timeline.append({"phase": current_phase, "start": start_index, "end": idx - 1, "messages": idx - start_index})
            current_phase = phase
            start_index = idx
    timeline.append({"phase": current_phase, "start": start_index, "end": len(messages) - 1, "messages": len(messages) - start_index})
    return timeline


def build_reflection(category_results: dict[str, CategoryResult]) -> str:
    planning = category_results["planning"].score
    debugging = category_results["debugging"].score
    iteration = category_results["iteration"].score
    constraints = category_results["constraints"].score
    return (
        "A good AI-assisted workflow is intentional, evidence-driven, and adaptive: "
        "the user plans clearly, iterates with targeted prompts, validates outputs, and corrects mistakes quickly. "
        f"In this session, planning={planning}, debugging={debugging}, iteration={iteration}, constraints={constraints}, "
        "so improvement should focus on low-scoring dimensions while preserving strong habits."
    )


def evaluate_workflow(messages: list[Message], settings: Settings, source_text: str | None = None) -> EvaluationResponse:
    category_results: dict[str, CategoryResult] = {}

    for category in CATEGORY_SPECS:
        category_results[category.name] = evaluate_category(
            messages,
            {
                "name": category.name,
                "description": category.description,
                "positive_signals": category.positive_signals,
                "negative_signals": category.negative_signals,
            },
            settings,
        )

    overall = round(mean(result.score for result in category_results.values()), 2)
    strengths, weaknesses, suggestions, summary = generate_insights(category_results)
    phase_timeline = build_phase_timeline(messages)
    format_source = source_text if source_text is not None else "\n".join(f"{m.role}: {m.content}" for m in messages)
    return EvaluationResponse(
        overall_score=overall,
        label=_label_from_score(overall),  # type: ignore[arg-type]
        categories=category_results,  # type: ignore[arg-type]
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions,
        summary=summary,
        reflection=build_reflection(category_results),
        transcript_format=detect_transcript_format(format_source),
        phase_timeline=phase_timeline,
        parsed_messages=len(messages),
    )
