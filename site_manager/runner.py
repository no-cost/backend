"""
Lower-level Ansible wrapper for tenant lifecycle management.
"""

import logging
import re
import time
from dataclasses import dataclass
from os import environ
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any

import sentry_sdk
from ansible_runner import Runner, RunnerConfig

from settings import VARS

ANSIBLE_ROOT = Path(__file__).parent.parent / "ansible"
ANSIBLE_TIMEOUT = int(environ.get("ANSIBLE_TIMEOUT", "900"))  # 15m

# values of these vars are cut out of the failure message and the output reported to Sentry
SECRET_VAR_PATTERN = re.compile(r"secret|token|password|key|database_url")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlaybookResult:
    """Outcome of a playbook run, read into memory because the run's artifact directory is removed afterwards."""

    status: str
    rc: int | None
    stdout: str
    stderr: str


class PlaybookError(RuntimeError):
    """A playbook run that didn't succeed, already reported to Sentry with its output."""


def run_playbook(
    playbook_path: str,
    tags: str | None = None,
    quiet: bool = True,
    extravars: dict[str, Any] = {},
    timeout: int | None = None,
) -> PlaybookResult:
    all_vars = VARS.copy()
    all_vars.update(extravars)

    target = extravars.get("tenant_tag") or "system"
    log_extra = {"playbook": playbook_path, "tenant_tag": extravars.get("tenant_tag", "")}
    logger.info("running %s (tags: %s) for %s", playbook_path, tags, target, extra=log_extra)
    started = time.monotonic()

    # /tmp is a tmpfs (RAM), every run's artifacts (output, events, the command line with all vars) are removed
    artifact_dir = mkdtemp(prefix="ansible-artifacts-")
    try:
        rc = RunnerConfig(
            private_data_dir=str(ANSIBLE_ROOT),
            artifact_dir=artifact_dir,
            playbook=playbook_path,  # relative to project dir: ansible/project/
            extravars=all_vars,
            envvars=dict[str, str](environ),
            tags=tags,
            quiet=quiet,
            timeout=timeout or ANSIBLE_TIMEOUT,
        )
        rc.prepare()

        runner = Runner(config=rc)
        runner.run()

        with runner.stdout as stdout, runner.stderr as stderr:
            result = PlaybookResult(
                status=runner.status,
                rc=runner.rc,
                stdout=stdout.read(),
                stderr=stderr.read(),
            )

        if result.status != "successful":
            stats = runner.stats
            error = PlaybookError(
                _redact(
                    f"Playbook {playbook_path} failed with status: {result.status}. rc: {result.rc}, stats: {stats}.\n\nstdout: {result.stdout}\nstderr: {result.stderr}",
                    all_vars,
                )
            )
            _report_failure(error, playbook_path, tags, extravars, all_vars, result, stats)
            raise error
    finally:
        rmtree(artifact_dir, ignore_errors=True)

    logger.info(
        "%s for %s finished in %.1fs", playbook_path, target, time.monotonic() - started, extra=log_extra
    )
    return result


def _report_failure(
    error: PlaybookError,
    playbook_path: str,
    tags: str | None,
    extravars: dict[str, Any],
    all_vars: dict[str, Any],
    result: PlaybookResult,
    stats: dict | None,
) -> None:
    """Report a failed run to Sentry with the full ansible output attached."""

    tenant_tag = extravars.get("tenant_tag")
    output = _redact(f"{result.stdout}\n\nstderr:\n{result.stderr}", all_vars)

    # a scope of its own, so the attachment doesn't end up in later events
    with sentry_sdk.new_scope() as scope:
        scope.set_tag("playbook", playbook_path)
        scope.set_tag("ansible_status", result.status)
        if tenant_tag:
            scope.set_tag("tenant_tag", tenant_tag)
        if extravars.get("tenant_hostname"):
            scope.set_tag("hostname", extravars["tenant_hostname"])
        scope.set_context(
            "ansible",
            {
                "playbook": playbook_path,
                "tags": tags,
                "status": result.status,
                "rc": result.rc,
                "stats": stats,
                "vars": {k: v for k, v in extravars.items() if not SECRET_VAR_PATTERN.search(k)},
            },
        )
        # the message contains the output, group by playbook instead
        scope.fingerprint = ["ansible-playbook-failed", playbook_path, tags or ""]
        scope.add_attachment(
            bytes=output.encode(),
            filename=f"ansible-{tenant_tag or Path(playbook_path).stem}.log",
            content_type="text/plain",
        )
        sentry_sdk.capture_exception(error)

    logger.warning(
        "%s for %s failed with status %s, rc %s",
        playbook_path,
        tenant_tag or "system",
        result.status,
        result.rc,
        extra={"playbook": playbook_path, "tenant_tag": tenant_tag or ""},
    )


def _redact(text: str, all_vars: dict[str, Any]) -> str:
    for name, value in all_vars.items():
        if isinstance(value, str) and value and SECRET_VAR_PATTERN.search(name):
            text = text.replace(value, f"[{name}]")
    return text


def provision_tenant(
    tenant_tag: str,
    service_type: str,
    hostname: str,
    admin_email: str,
    reset_token: str,
    force: bool = False,
    send_email: bool = True,
) -> PlaybookResult:
    """Provision a new tenant using Ansible."""

    return run_playbook(
        "provision_main.yml",
        tags="send-email" if send_email else None,
        extravars={
            "tenant_tag": tenant_tag,
            "tenant_hostname": hostname,
            "service_type": service_type,
            "tenant_admin_email": admin_email,
            "tenant_reset_token": reset_token,
            "force": force,
        },
    )


def remove_tenant(
    tenant_tag: str,
    service_type: str,
    skip_backup: bool = False,
    send_email: bool = True,
    admin_email: str | None = None,
    hostname: str | None = None,
    reason: str | None = None,
) -> PlaybookResult:
    """Remove a tenant using Ansible."""

    return run_playbook(
        "backup_main.yml",
        extravars={
            "tenant_tag": tenant_tag,
            "service_type": service_type,
            "skip_backup": skip_backup,
            "send_email": send_email,
            "tenant_admin_email": admin_email or "",
            "tenant_hostname": hostname or "",
            "removal_reason": reason or "",
        },
    )


def backup_tenant(
    tenant_tag: str,
    service_type: str,
    periodic: bool = False,
    delete_older_than_days: int = 7,
    include_private: bool = True,
    backup_dir: str | None = None,
    include_readme: bool = False,
) -> PlaybookResult:
    """Backup a tenant using Ansible, `include_private` adds etc/config.json (credentials) and logs."""

    extravars: dict[str, Any] = {
        "tenant_tag": tenant_tag,
        "service_type": service_type,
        "skip_backup": False,
        "delete_older_than_days": delete_older_than_days,
        "include_private": include_private,
        "include_readme": include_readme,
    }
    if backup_dir:
        extravars["backup_dir_override"] = backup_dir

    return run_playbook(
        "backup_main.yml",
        tags="periodic" if periodic else "backup",
        extravars=extravars,
    )


def restore_tenant(
    tenant_tag: str,
    service_type: str,
    backup_mode: str = "attic",
    backup_date: str | None = None,
) -> PlaybookResult:
    """Restore a tenant from backup."""

    extravars: dict[str, Any] = {
        "tenant_tag": tenant_tag,
        "service_type": service_type,
    }
    if backup_date:
        extravars["backup_date"] = backup_date

    return run_playbook(
        "restore_main.yml",
        tags=backup_mode,
        extravars=extravars,
    )


def sync_tenant_files(
    tenant_tag: str,
    service_type: str,
) -> PlaybookResult:
    return run_playbook(
        "sync_files_main.yml",
        extravars={
            "tenant_tag": tenant_tag,
            "service_type": service_type,
        },
    )


def backup_system(
    delete_older_than_days: int = 7,
) -> PlaybookResult:
    return run_playbook(
        "backup_system_main.yml",
        extravars={
            "delete_older_than_days": delete_older_than_days,
        },
    )
