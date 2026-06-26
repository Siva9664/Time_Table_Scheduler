from fastapi import APIRouter
from .endpoints import timetable, imports, auth

api_router = APIRouter()
api_router.include_router(timetable.router, prefix="", tags=["timetable"])
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

