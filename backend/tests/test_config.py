import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings, settings
from app.core.logging_config import configure_logging


class TestConfigSettings:
    def test_default_settings_properties(self):
        assert settings.ALGORITHM == "HS256"
        assert settings.SOLVER_TIME_LIMIT_SECONDS > 0
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert isinstance(settings.origins_list, list)
        assert len(settings.origins_list) > 0

    def test_origins_list_parsing_and_trimming(self):
        custom_settings = Settings(
            ALLOWED_ORIGINS="http://localhost:3000, http://example.com,https://scheduler.app "
        )
        origins = custom_settings.origins_list
        assert origins == ["http://localhost:3000", "http://example.com", "https://scheduler.app"]

    def test_active_mongodb_url_toggle(self):
        atlas_settings = Settings(
            USE_LOCAL_MONGODB=False,
            MONGODB_URL="mongodb+srv://atlas_user:pass@cluster.mongodb.net",
            LOCAL_MONGODB_URL="mongodb://localhost:27017",
        )
        assert atlas_settings.active_mongodb_url == "mongodb+srv://atlas_user:pass@cluster.mongodb.net"

        local_settings = Settings(
            USE_LOCAL_MONGODB=True,
            MONGODB_URL="mongodb+srv://atlas_user:pass@cluster.mongodb.net",
            LOCAL_MONGODB_URL="mongodb://127.0.0.1:27017",
        )
        assert local_settings.active_mongodb_url == "mongodb://127.0.0.1:27017"

    def test_active_ai_api_key_priority(self):
        # 1. Qwen key takes precedence
        s1 = Settings(QWEN_API_KEY="key-qwen", DASHSCOPE_API_KEY="key-dash", OPENAI_API_KEY="key-openai")
        assert s1.active_ai_api_key == "key-qwen"

        # 2. Dashscope key if no Qwen
        s2 = Settings(QWEN_API_KEY=None, DASHSCOPE_API_KEY="key-dash", OPENAI_API_KEY="key-openai")
        assert s2.active_ai_api_key == "key-dash"

        # 3. Fallback to OpenAI key
        s3 = Settings(QWEN_API_KEY=None, DASHSCOPE_API_KEY=None, OPENAI_API_KEY="key-openai")
        assert s3.active_ai_api_key == "key-openai"

    def test_active_document_analysis_model_fallback(self):
        # Fallback away from outdated local models to qwen3:1.7b
        s_local = Settings(DOCUMENT_ANALYSIS_MODEL="local")
        assert s_local.active_document_analysis_model == "qwen3:1.7b"

        s_custom = Settings(DOCUMENT_ANALYSIS_MODEL="custom-vision-v2")
        assert s_custom.active_document_analysis_model == "custom-vision-v2"


class TestLoggingConfiguration:
    def test_configure_logging_runs_without_exception(self):
        # Ensure loguru intercept handler configuration executes cleanly
        configure_logging()
        assert True
