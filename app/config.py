import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    groq_api_key: str
    groq_model: str
    max_document_size_mb: int


def get_settings() -> Settings:
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    max_document_size_mb = int(
        os.getenv("MAX_DOCUMENT_SIZE_MB", "20")
    )

    if not telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured")

    if not groq_api_key:
        raise ValueError("GROQ_API_KEY is not configured")

    if max_document_size_mb <= 0:
        raise ValueError("MAX_DOCUMENT_SIZE_MB must be greater than 0")

    return Settings(
        telegram_bot_token=telegram_bot_token,
        groq_api_key=groq_api_key,
        groq_model=groq_model,
        max_document_size_mb=max_document_size_mb,
    )
