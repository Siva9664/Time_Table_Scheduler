from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    USE_LOCAL_MONGODB: bool = False
    LOCAL_MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "timetable_db"
    SECRET_KEY: str = "supersecretkey123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 4320 # 3 days
    ALLOWED_ORIGINS: str = "http://localhost:3002,http://localhost:3000,http://localhost:3003,http://localhost:5173"
    SOLVER_TIME_LIMIT_SECONDS: int = 60
    AI_MODEL: str = "grok-1"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT_SECONDS: int = 60
    DOCUMENT_UPLOAD_MAX_FILES: int = 10
    DOCUMENT_UPLOAD_MAX_FILE_BYTES: int = 15 * 1024 * 1024
    DOCUMENT_TEXT_MAX_CHARS: int = 200_000
    DOCUMENT_OCR_MAX_PAGES: int = 6
    DOCUMENT_ANALYSIS_MODEL: Optional[str] = None
    DOCUMENT_ANALYSIS_API_BASE: str = "http://localhost:11434/v1"
    DOCUMENT_ANALYSIS_API_KEY: Optional[str] = "local"
    DOCUMENT_ANALYSIS_TIMEOUT_SECONDS: int = 120
    DOCUMENT_ANALYSIS_MAX_CHARS: int = 60_000

    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def active_mongodb_url(self) -> str:
        return self.LOCAL_MONGODB_URL if self.USE_LOCAL_MONGODB else self.MONGODB_URL

    class Config:
        env_file = BACKEND_DIR / ".env"

settings = Settings()
