import asyncio
import os
import shutil

from settings import VARS
from utils.cmd import run_cmd

REQUIRED_SERVICES = ["mariadb", f"php{VARS['php_version']}-fpm", "nginx"]


async def check_services() -> dict[str, str]:
    """Check whether required systemd services are active."""
    results = {}
    for service in REQUIRED_SERVICES:
        proc = await run_cmd(
            f"systemctl is-active {service}",
            check=False,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout = await proc.stdout.read()
        results[service] = stdout.decode().strip()
    return results


async def get_health_status() -> dict:
    """Return full health status including services, load, and disk usage."""
    load_1m, load_5m, load_15m = os.getloadavg()
    disk = shutil.disk_usage("/")
    disk_usage_percent = round(disk.used / disk.total * 100, 1)

    services = await check_services()
    # "reloading" means the service is still running, just re-reading config
    services_ok = all(s in ("active", "reloading") for s in services.values())

    if not services_ok:
        status = "services_down"
    elif disk_usage_percent > 90:
        status = "disk_critical"
    else:
        status = "ok"

    return {
        "status": status,
        "services": services,
        "load_1m": round(load_1m, 2),
        "load_5m": round(load_5m, 2),
        "load_15m": round(load_15m, 2),
        "disk_usage_percent": disk_usage_percent,
        "disk_free_gb": round(disk.free / (1024**3), 2),
    }
