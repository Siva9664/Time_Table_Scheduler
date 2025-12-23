from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.router import api_router
from .core.config import settings
from .database.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Timetable Scheduler", description="Dynamic timetable scheduling using OR-Tools", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=settings.origins_list, allow_credentials=True,
                  allow_methods=["*"], allow_headers=["*"])

app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "AI Timetable Scheduler API", "docs": "/docs", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}
