import json
import logging
from pathlib import Path

from settings import VARS


MAX_BRANDING_UPLOAD_SIZE = 3 * 1024 * 1024  # 3 MB
ALLOWED_LANGUAGES = {
    "en",
    "de",
    "fr",
    "es",
    "it",
    "pt",
    "nl",
    "pl",
    "ua",
    "ja",
    "zh",
    "ko",
    "ar",
    "cs",
    "sk",
}
ALLOWED_BRANDING_IMAGE_TYPES = {
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "image/jpeg": ".jpg",
}


def get_default_mediawiki_skins() -> list[str]:
    skins_dir = (
        Path(VARS["paths"]["tenants"]["skeleton_root"])
        / "mediawiki"
        / "app"
        / "public"
        / "skins"
    )

    skin_names: list[str] = []
    for skin_path in skins_dir.iterdir():
        skin_json = skin_path / "skin.json"
        if not skin_json.is_file():
            continue

        try:
            data: dict[str, dict[str, str]] = json.loads(skin_json.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"failed to read {skin_json}: {e}")
            continue

        for name in data.get("ValidSkinNames", {}).values():
            skin_names.append(name.lower())

    return skin_names


ALLOWED_DEFAULT_SKINS = get_default_mediawiki_skins()
