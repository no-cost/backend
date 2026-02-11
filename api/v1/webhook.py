import json
import logging
import re
import typing as t

import fastapi as fa
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Site
from database.session import get_session
from settings import VARS
from site_manager.tenant_config import update_config
from utils import send_mail

logger = logging.getLogger(__name__)

V1_WEBHOOK = fa.APIRouter(prefix="/webhook", tags=["webhook"])


class KofiData(BaseModel):
    verification_token: str
    message_id: str
    timestamp: str
    type: str
    is_public: bool
    from_name: str
    message: str | None
    amount: str
    url: str
    email: str
    currency: str
    is_subscription_payment: bool
    is_first_subscription_payment: bool
    kofi_transaction_id: str
    shop_items: list | None = None
    tier_name: str | None = None


@V1_WEBHOOK.post("/kofi")
async def kofi_webhook(
    data: t.Annotated[str, fa.Form()],
    db: t.Annotated[AsyncSession, fa.Depends(get_session)],
):
    try:
        payload = KofiData(**json.loads(data))
    except (json.JSONDecodeError, Exception):
        raise fa.HTTPException(status_code=400, detail="Invalid payload")

    if payload.verification_token != VARS["kofi_verification_token"]:
        raise fa.HTTPException(status_code=403, detail="Invalid verification token")

    amount = float(payload.amount)

    # try matching by message first (donor can include their site tag),
    site = None
    if payload.message:
        just_host = re.sub(r"^https?://", "", payload.message)
        just_host = just_host.split("/")[0]
        just_host = re.sub(r"[^\w.\-]", "", just_host)
        if just_host:
            site = await Site.get_by_identifier(db, just_host)

    # fall back to email
    if site is None:
        site = await Site.get_by_identifier(db, payload.email)

    if site is None:
        send_mail(
            to=VARS["info_mail"],
            subject="Ko-fi webhook: donor not found",
            body=(
                f"A Ko-fi donation of {payload.amount} {payload.currency} "
                f"was received from '{payload.from_name}' ({payload.email}), "
                f"but no active site with this email was found.\n\n"
                f"Transaction: {payload.kofi_transaction_id}\n"
                f"Message: {payload.message or '(none)'}"
            ),
        )
        return {"status": "ok"}  # so ko-fi is happy

    site.donated_amount = (site.donated_amount or 0.0) + amount
    await db.commit()

    update_config(site, {"donated_amount": site.donated_amount})

    return {"status": "ok"}
