"""Langfuse tracing (SDK v2) — matches self-hosted Langfuse server v2.x.

If Langfuse keys aren't configured, the decorator is a no-op so nothing
breaks for local-only runs.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable

from checkmate.config import settings

logger = logging.getLogger(__name__)

_ENABLED = bool(settings.langfuse_public_key and settings.langfuse_secret_key)

if _ENABLED:
    # Langfuse SDK reads these from env on import.
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

    from langfuse.decorators import langfuse_context, observe  # type: ignore

    logger.info("Langfuse tracing enabled → %s", settings.langfuse_host)
else:
    logger.info("Langfuse tracing disabled (keys not set)")

    langfuse_context = None  # type: ignore

    def observe(*dargs: Any, **dkwargs: Any) -> Callable:
        """No-op stand-in matching Langfuse's @observe() signature."""
        if len(dargs) == 1 and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def decorator(func: Callable) -> Callable:
            return func

        return decorator


def update_generation(**kwargs: Any) -> None:
    """Attach metadata (usage, model, cost) to the current generation span.

    In SDK v2 both spans and generations use the same update method.
    """
    if langfuse_context is None:
        return
    try:
        langfuse_context.update_current_observation(**kwargs)
    except Exception:
        logger.debug("update_current_observation failed", exc_info=True)


def update_span(**kwargs: Any) -> None:
    if langfuse_context is None:
        return
    try:
        langfuse_context.update_current_observation(**kwargs)
    except Exception:
        logger.debug("update_current_observation failed", exc_info=True)


def update_trace(**kwargs: Any) -> None:
    if langfuse_context is None:
        return
    try:
        langfuse_context.update_current_trace(**kwargs)
    except Exception:
        logger.debug("update_current_trace failed", exc_info=True)


def flush() -> None:
    """Force-flush pending events — call at worker shutdown or in smoke tests."""
    if langfuse_context is None:
        return
    try:
        langfuse_context.flush()
    except Exception:
        logger.debug("langfuse flush failed", exc_info=True)


__all__ = ["observe", "update_generation", "update_span", "update_trace", "flush"]
