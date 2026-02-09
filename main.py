from fastapi import FastAPI

from api.v1 import V1

API = FastAPI(title="no-cost API", description="API for no-cost.site")
API.include_router(V1)
