import fastapi as fa
import httpx

from settings import VARS

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str) -> None:
    """Verify a Cloudflare Turnstile token. Raises HTTPException on failure."""

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            VERIFY_URL,
            json={"secret": VARS["turnstile_key"], "response": token},
            timeout=5,
        )

    if not resp.json().get("success", False):
        raise fa.HTTPException(status_code=400, detail="Turnstile verification failed")
