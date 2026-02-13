import os
import shutil

import fastapi as fa
from api.v1.account import V1_ACCOUNT
from api.v1.settings import V1_SETTINGS
from api.v1.signup import V1_SIGNUP
from api.v1.webhook import V1_WEBHOOK
from settings import VARS

V1 = fa.APIRouter(prefix="/v1")


@V1.get("/")
async def index():
    return {"status": "ok", "version": "1.0.0"}


@V1.get("/health-check")
async def health_check(x_token: str = fa.Header()):
    if x_token != VARS["health_check_token"]:
        raise fa.HTTPException(status_code=403, detail="Invalid token")

    load_1m, load_5m, load_15m = os.getloadavg()
    disk = shutil.disk_usage("/")

    disk_usage_percent = round(disk.used / disk.total * 100, 1)

    return {
        "status": "ok" if disk_usage_percent <= 90 else "disk_critical",
        "load_1m": round(load_1m, 2),
        "load_5m": round(load_5m, 2),
        "load_15m": round(load_15m, 2),
        "disk_usage_percent": disk_usage_percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
    }


V1.include_router(V1_ACCOUNT)
V1.include_router(V1_SIGNUP)
V1.include_router(V1_SETTINGS)
V1.include_router(V1_WEBHOOK)
