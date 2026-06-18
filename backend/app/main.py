from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .api.router import api_router
from .core.config import settings
from .core.logging_config import configure_logging
from .database.database import get_client, close_mongo_connection
import time
import logging
from urllib.parse import urlsplit, urlunsplit

# Initialize Logging
configure_logging()

logger = logging.getLogger(__name__)

def _mask_mongo_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        if "@" not in parts.netloc:
            return url
        host = parts.netloc.rsplit("@", 1)[1]
        return urlunsplit((parts.scheme, f"***:***@{host}", parts.path, parts.query, parts.fragment))
    except Exception:
        return "<configured MongoDB URL>"

app = FastAPI(title="AI Timetable Scheduler", description="Dynamic timetable scheduling using OR-Tools", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=settings.origins_list, allow_credentials=True,
                  allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(f"Method: {request.method} Path: {request.url.path} Status: {response.status_code} Time: {process_time:.2f}ms")
    return response

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    try:
        client = get_client()
        client.admin.command("ping")
        logger.info(f"[SUCCESS] Connected to MongoDB at {_mask_mongo_url(settings.active_mongodb_url)} | DB: {settings.DB_NAME}")
    except Exception as e:
        logger.error(f"[ERROR] Could not connect to MongoDB: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    close_mongo_connection()

app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {"message": "AI Timetable Scheduler API", "docs": "/docs", "version": "1.0.0"}

@app.get("/health")
def health():
    logger.debug("Health check probe")
    return {"status": "healthy"}
