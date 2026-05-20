from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
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

    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"

settings = Settings()
