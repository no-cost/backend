from fastapi import FastAPI

from api.v1 import V1

API = FastAPI(title="FreeFlarum API", description="API for FreeFlarum")
API.include_router(V1)
