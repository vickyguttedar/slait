from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategorySpec:
    name: str
    description: str
    positive_signals: list[str]
    negative_signals: list[str]


CATEGORY_SPECS: list[CategorySpec] = [
    CategorySpec(
        name="planning",
        description="How clearly the user defines objectives, steps, and constraints before implementation.",
        positive_signals=["breaks work into steps", "states priorities", "defines success criteria"],
        negative_signals=["jumps straight to coding", "unclear goals", "constant direction changes"],
    ),
    CategorySpec(
        name="debugging",
        description="How systematically issues are diagnosed and validated.",
        positive_signals=["forms hypotheses", "collects evidence", "tests one change at a time"],
        negative_signals=["random retries", "no error analysis", "no verification"],
    ),
    CategorySpec(
        name="constraints",
        description="How well the user accounts for requirements, limits, and edge cases.",
        positive_signals=["mentions requirements", "calls out edge cases", "tracks scope boundaries"],
        negative_signals=["ignores constraints", "scope creep", "misses non-functional requirements"],
    ),
    CategorySpec(
        name="iteration",
        description="How effectively outputs are refined through feedback loops.",
        positive_signals=["small iterative improvements", "specific follow-up requests", "quality tightening"],
        negative_signals=["one-shot prompting", "vague refinements", "no adaptation"],
    ),
    CategorySpec(
        name="correction",
        description="How quickly and clearly mistakes are recognized and corrected.",
        positive_signals=["acknowledges mistakes", "requests corrections", "updates assumptions"],
        negative_signals=["repeats known mistakes", "ignores wrong outputs", "unclear correction intent"],
    ),
    CategorySpec(
        name="tool_usage",
        description="How well AI tools and context are used to accelerate coding outcomes.",
        positive_signals=["uses relevant tools", "provides context files", "asks for verification"],
        negative_signals=["misuses tools", "insufficient context", "ignores tool outputs"],
    ),
    CategorySpec(
        name="repetition",
        description="How much avoidable repetition exists in prompts or actions.",
        positive_signals=["reuses reusable patterns", "avoids duplicated asks", "consolidates requests"],
        negative_signals=["repeated vague prompts", "duplicate retries", "same failed ask without change"],
    ),
]
