from fastapi import FastAPI

from api.v1 import V1

FF_API = FastAPI(title="FreeFlarum API", description="API for FreeFlarum")
FF_API.include_router(V1)
