import json
from pathlib import Path

from database.models import Site
from settings import VARS

type config_dict = dict[str, str | int | float | bool | None]


def load_config(site: Site) -> config_dict:
    config_path = (
        Path(VARS["paths"]["tenants"]["root"]) / site.tag / "etc" / "config.json"
    )

    return json.loads(config_path.read_text())


def update_config(site: Site, to_merge: config_dict) -> None:
    config_path = (
        Path(VARS["paths"]["tenants"]["root"]) / site.tag / "etc" / "config.json"
    )
    config: config_dict = load_config(site)

    config.update(to_merge)
    config_path.write_text(json.dumps(config, indent=2) + "\n")
