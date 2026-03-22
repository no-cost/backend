import fastapi as fa

from api.v1.account import V1_ACCOUNT
from api.v1.settings import V1_SETTINGS
from api.v1.signup import V1_SIGNUP
from api.v1.webhook import V1_WEBHOOK
from settings import VARS
from utils.health import get_health_status

V1 = fa.APIRouter(prefix="/v1")


@V1.get("/")
async def index():
    return {"status": "ok", "version": "1.0.0"}


@V1.get("/health-check")
async def health_check(x_token: str = fa.Header()):
    if x_token != VARS["health_check_token"]:
        raise fa.HTTPException(status_code=403, detail="Invalid token")

    return await get_health_status()


V1.include_router(V1_ACCOUNT)
V1.include_router(V1_SIGNUP)
V1.include_router(V1_SETTINGS)
V1.include_router(V1_WEBHOOK)
