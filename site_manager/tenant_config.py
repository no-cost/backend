import asyncio
import json
import tempfile
from pathlib import Path

from database.models import Site
from settings import VARS
from utils.cmd import run_cmd

type config_dict = dict[str, str | int | float | bool | None]


def _config_path(site: Site) -> Path:
    return Path(VARS["paths"]["tenants"]["root"]) / site.tag / "etc" / "config.json"


# using sudo here to avoid permission issues (because config is owned by tenant)


async def load_config(site: Site) -> config_dict:
    path = _config_path(site)
    proc = await asyncio.create_subprocess_exec(
        f"sudo cat {path}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to read {path}: {stderr.decode()}")

    return json.loads(stdout.decode())


async def update_config(site: Site, to_merge: config_dict) -> None:
    config: config_dict = await load_config(site)
    config.update(to_merge)

    path = _config_path(site)
    tenant_user = f"tenant_{site.tag}"
    content = json.dumps(config, indent=2) + "\n"

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    await run_cmd(f"sudo mv {tmp_path} {path}")
    await run_cmd(f"sudo chmod 640 {path}")
    await run_cmd(f"sudo chown {tenant_user}:{tenant_user} {path}")
