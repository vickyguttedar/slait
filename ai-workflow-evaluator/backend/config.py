from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openai_api_key: str | None
    model_name: str
    max_chunk_chars: int


def load_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        max_chunk_chars=int(os.getenv("MAX_CHUNK_CHARS", "5000")),
    )
