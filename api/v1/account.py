import fastapi as fa

V1_ACCOUNT = fa.APIRouter(prefix="/account")


@V1_ACCOUNT.get("/")
async def account():
    return {"message": "Hello, World!"}
