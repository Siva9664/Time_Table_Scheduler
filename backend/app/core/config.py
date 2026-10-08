from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    USE_LOCAL_MONGODB: bool = False
    LOCAL_MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "timetable_db"
    SECRET_KEY: str = "supersecretkey123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 4320  # 3 days
    ALLOWED_ORIGINS: str = (
        "http://localhost:3002,http://localhost:3000,http://localhost:3003,http://localhost:5173"
    )
    SOLVER_TIME_LIMIT_SECONDS: int = 60
    AI_MODEL: str = "qwen3:1.7b"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "http://localhost:11434/v1"
    OPENAI_TIMEOUT_SECONDS: int = 120
    DOCUMENT_UPLOAD_MAX_FILES: int = 10
    DOCUMENT_UPLOAD_MAX_FILE_BYTES: int = 15 * 1024 * 1024
    DOCUMENT_TEXT_MAX_CHARS: int = 200_000
    DOCUMENT_OCR_MAX_PAGES: int = 6
    DOCUMENT_ANALYSIS_MODEL: str = "qwen3:1.7b"
    QWEN_API_KEY: Optional[str] = None
    DASHSCOPE_API_KEY: Optional[str] = None
    DOCUMENT_ANALYSIS_API_BASE: str = "http://localhost:11434/v1"
    DOCUMENT_ANALYSIS_API_KEY: Optional[str] = "ollama"
    DOCUMENT_ANALYSIS_TIMEOUT_SECONDS: int = 120
    DOCUMENT_ANALYSIS_MAX_CHARS: int = 60_000

    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def active_mongodb_url(self) -> str:
        return self.LOCAL_MONGODB_URL if self.USE_LOCAL_MONGODB else self.MONGODB_URL

    @property
    def active_ai_api_key(self) -> Optional[str]:
        return self.QWEN_API_KEY or self.DASHSCOPE_API_KEY or self.OPENAI_API_KEY or self.DOCUMENT_ANALYSIS_API_KEY or "ollama"

    @property
    def active_ai_api_base(self) -> str:
        return self.DOCUMENT_ANALYSIS_API_BASE or "http://localhost:11434/v1"

    @property
    def active_ai_model(self) -> str:
        return self.DOCUMENT_ANALYSIS_MODEL or "qwen3:1.7b"

    @property
    def active_document_analysis_model(self) -> Optional[str]:
        if self.DOCUMENT_ANALYSIS_MODEL is None:
            return None
        if not self.DOCUMENT_ANALYSIS_MODEL or self.DOCUMENT_ANALYSIS_MODEL in ("local", "qwen3:8b", "qwen2.5vl"):
            return "qwen3:1.7b"
        return self.DOCUMENT_ANALYSIS_MODEL

    @property
    def active_document_analysis_api_key(self) -> Optional[str]:
        if self.DOCUMENT_ANALYSIS_MODEL is None:
            return None
        return self.QWEN_API_KEY or self.DOCUMENT_ANALYSIS_API_KEY or "ollama"

    @property
    def active_document_analysis_api_base(self) -> str:
        return self.DOCUMENT_ANALYSIS_API_BASE or "http://localhost:11434/v1"

    class Config:
        env_file = BACKEND_DIR / ".env"
        extra = "ignore"


settings = Settings()

