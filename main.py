from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import V1
from settings import VARS

API = FastAPI(title="no-cost API", description="API for no-cost.site")

API.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"https://{VARS['main_domain']}",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API.include_router(V1)
