from fastapi import APIRouter
from .endpoints import timetable, imports

api_router = APIRouter()
api_router.include_router(timetable.router, prefix="", tags=["timetable"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
