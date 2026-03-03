from pydantic_settings import BaseSettings
from typing import List

import os

class Settings(BaseSettings):
    # Go up 3 levels from app/core/config.py to reach backend root
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATABASE_URL: str = f"sqlite:///{os.path.join(BASE_DIR, 'sql_app.db')}"
    SECRET_KEY: str = "supersecretkey123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 4320 # 3 days
    ALLOWED_ORIGINS: str = "http://localhost:3002,http://localhost:3000,http://localhost:3003,http://localhost:5173"
    SOLVER_TIME_LIMIT_SECONDS: int = 60
    GEMINI_API_KEY: str = ""

    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"

settings = Settings()
