from fastapi import APIRouter, Depends

from app.api.query_params import reject_unknown_query_params
from app.api.v1 import catalog, dashboard, observations, states

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(reject_unknown_query_params)])
api_router.include_router(catalog.router)
api_router.include_router(observations.router)
api_router.include_router(dashboard.router)
api_router.include_router(states.router)
