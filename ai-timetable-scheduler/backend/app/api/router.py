from fastapi import APIRouter
from .endpoints import auth, timetable

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(timetable.router, prefix="", tags=["timetable"])
