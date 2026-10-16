"""
Error and log reporting to Sentry, enabled by the SENTRY_DSN environment variable.

Once initialised, unhandled exceptions (API requests and background tasks, CLI commands) and
`logger.error()`/`logger.exception()` records become Sentry events, and `logging` records from INFO up
are sent as Sentry Logs.
"""

import logging
from contextlib import suppress
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.argv import ArgvIntegration
from sentry_sdk.integrations.logging import ignore_logger

from settings import VARS

# per-request access logs (URLs can carry tokens) would only burn the Sentry Logs quota
_IGNORED_LOGGERS = {"uvicorn.access", "gunicorn.access"}
_REPORTED_ATTR = "_sentry_reported"
_SECRET_HEADER_PARTS = ("token", "secret", "auth", "cookie", "key")


def init_sentry(component: str) -> None:
    """
    Set up logging (INFO and up) and, with SENTRY_DSN set, Sentry reporting tagged with `component`:
    "api" or the CLI command name. Call once at the entry point, before anything else runs.
    """

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    if not VARS["sentry_dsn"]:
        return

    def before_send_log(log: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
        if log["attributes"].get("logger.name") in _IGNORED_LOGGERS:
            return None
        log["attributes"]["component"] = component
        return log

    for name in _IGNORED_LOGGERS:
        ignore_logger(name)

    sentry_sdk.init(
        dsn=VARS["sentry_dsn"],
        environment=VARS["sentry_environment"],
        enable_logs=True,
        before_send=_before_send,
        before_send_log=before_send_log,
        # no secrets in events: request bodies hold passwords and the Ko-fi verification token,
        # stack frames hold VARS (JWT secret, database URL, ...), CLI arguments can hold passwords
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        disabled_integrations=[ArgvIntegration()],
    )
    sentry_sdk.get_global_scope().set_tag("component", component)


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    exc_info = hint.get("exc_info")
    if exc_info:
        # an exception (or its cause) is reported once, by whoever has the most context: e.g. a failed playbook
        # is reported with its output by the runner, then not again when it's unhandled in a CLI command or API
        # background task, logged by a caller with `logger.exception()` or wrapped in an HTTP 500 response
        error = exc_info[1]
        seen: set[int] = set()
        while error is not None and id(error) not in seen:
            if getattr(error, _REPORTED_ATTR, False):
                return None
            seen.add(id(error))
            error = error.__cause__ or error.__context__

        with suppress(AttributeError):
            setattr(exc_info[1], _REPORTED_ATTR, True)

    # query strings and headers can carry tokens (/account/export?token=..., x-token, x-test-token)
    request = event.get("request")
    if request:
        request.pop("query_string", None)
        if isinstance(request.get("url"), str):
            request["url"] = request["url"].split("?", 1)[0]
        headers = request.get("headers")
        if isinstance(headers, dict):
            for name in headers:
                if any(part in name.lower() for part in _SECRET_HEADER_PARTS):
                    headers[name] = "[Filtered]"

    return event
