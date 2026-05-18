from fastapi import APIRouter
from .endpoints import timetable

api_router = APIRouter()
api_router.include_router(timetable.router, prefix="", tags=["timetable"])
