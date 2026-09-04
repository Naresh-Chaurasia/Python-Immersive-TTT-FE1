"""
config.py — packaged_service_example

Environment and secrets handling pattern for a deployable service. This is the same
`.env`/`os.environ` idea from Week 2's `01_working_with_apis.ipynb`, extended with the
validation and fail-fast behaviour a real deployed service needs (Week 2 didn't need to
fail loudly on a missing key in a learning notebook; a production service does).
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_api_key: str
    llm_model: str
    log_level: str
    port: int

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            # Fail closed and fail loudly — a missing key should stop startup,
            # never silently proceed with a broken/empty credential.
            raise RuntimeError(
                "LLM_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        return cls(
            llm_api_key=api_key,
            llm_model=os.environ.get("LLM_MODEL", "gpt-demo"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            port=int(os.environ.get("PORT", "8000")),
        )
