import typing as t

import fastapi as fa

from database.models import Site
from utils.auth import get_current_site


def require_site_type(expected_type: str):
    async def _check(
        site: t.Annotated[Site, fa.Depends(get_current_site)],
    ) -> Site:
        if site.site_type != expected_type:
            raise fa.HTTPException(
                status_code=400,
                detail=f"This endpoint is only available for {expected_type} sites",
            )
        return site

    return _check
