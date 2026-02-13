import typing as t

import fastapi as fa

from api.v1.service_settings import require_site_type
from database.models import Site
from site_manager import write_tenant_file
from site_manager.tenant_config import load_config, update_config

MEDIAWIKI = fa.APIRouter(prefix="/mediawiki", tags=["mediawiki"])

MAX_BRANDING_UPLOAD_SIZE = 3 * 1024 * 1024  # 4 MB
ALLOWED_DEFAULT_SKINS = {"vector-2022", "citizen", "minerva", "timeless"}
ALLOWED_BRANDING_IMAGE_TYPES = {
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "image/jpeg": ".jpg",
}


@MEDIAWIKI.get("/")
async def get_settings(
    site: t.Annotated[Site, fa.Depends(require_site_type("mediawiki"))],
) -> dict:
    return (await load_config(site)).get("mediawiki", {})


@MEDIAWIKI.get("/default-skin")
async def get_default_skins(
    _site: t.Annotated[Site, fa.Depends(require_site_type("mediawiki"))],
) -> list[str]:
    return sorted(ALLOWED_DEFAULT_SKINS)


@MEDIAWIKI.patch("/default-skin")
async def set_default_skin(
    skin: t.Annotated[str, fa.Body(embed=True)],
    site: t.Annotated[Site, fa.Depends(require_site_type("mediawiki"))],
) -> dict:
    if skin not in ALLOWED_DEFAULT_SKINS:
        raise fa.HTTPException(
            status_code=422,
            detail=f"Invalid default skin. Allowed: {', '.join(sorted(ALLOWED_DEFAULT_SKINS))}",
        )
    await _set_mw_conf(site, "skin", skin)
    return {"skin": skin}


@MEDIAWIKI.get("/logo")
async def get_logo(
    site: t.Annotated[Site, fa.Depends(require_site_type("mediawiki"))],
) -> dict:
    mw = (await load_config(site)).get("mediawiki", {})
    return {"logo": mw.get("logo")}


@MEDIAWIKI.get("/favicon")
async def get_favicon(
    site: t.Annotated[Site, fa.Depends(require_site_type("mediawiki"))],
) -> dict:
    mw = (await load_config(site)).get("mediawiki", {})
    return {"favicon": mw.get("favicon")}


@MEDIAWIKI.put("/logo")
async def upload_logo(
    file: fa.UploadFile,
    site: t.Annotated[Site, fa.Depends(require_site_type("mediawiki"))],
) -> dict:
    url = await _upload_branding(site, file, "logo", "/images/branding/logo")
    return {"logo": url}


@MEDIAWIKI.put("/favicon")
async def upload_favicon(
    file: fa.UploadFile,
    site: t.Annotated[Site, fa.Depends(require_site_type("mediawiki"))],
) -> dict:
    url = await _upload_branding(site, file, "favicon", "/favicon")
    return {"favicon": url}


async def _upload_branding(
    site: Site, file: fa.UploadFile, asset: str, dest_rel: str
) -> str:
    ext = ALLOWED_BRANDING_IMAGE_TYPES.get(file.content_type)
    if ext is None:
        raise fa.HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{file.content_type}'",
        )

    content = await file.read(MAX_BRANDING_UPLOAD_SIZE + 1)
    if len(content) > MAX_BRANDING_UPLOAD_SIZE:
        raise fa.HTTPException(status_code=413, detail="File too large (max 2 MB)")

    url_path = f"{dest_rel}{ext}"
    await write_tenant_file(site, f"app/public{url_path}", content)
    await _set_mw_conf(site, asset, url_path)
    return url_path


async def _set_mw_conf(site: Site, key: str, value: str) -> None:
    config = await load_config(site)
    mw = config.get("mediawiki", {})
    mw[key] = value
    await update_config(site, {"mediawiki": mw})
