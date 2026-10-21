from fastapi import APIRouter

from app.api.v1 import catalog, observations

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(catalog.router)
api_router.include_router(observations.router)
