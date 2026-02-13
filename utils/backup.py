from pathlib import Path

from settings import VARS


def get_attic_backup_path(tag: str) -> Path:
    return Path(VARS["paths"]["backup_attic_root"]) / f"{tag}.tar.gz"


def get_latest_host_backup(tag: str) -> Path | None:
    backup_dir = Path(VARS["paths"]["backup_host_root"]) / tag
    if not backup_dir.is_dir():
        return None

    archives = sorted(backup_dir.glob("*.tar.gz"), reverse=True)
    return archives[0] if archives else None
