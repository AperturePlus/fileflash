from __future__ import annotations

import logging

from ...core.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Bump when changing Agent API behavior (visible in GET /agent/status).
AGENT_API_BUILD = "2026-05-18-r2"


def log_agent_settings(settings: Settings | None = None, *, endpoint: str) -> Settings:
    """Log effective Agent config on each API call (no 503 disable gate)."""
    settings = settings or get_settings()
    logger.info(
        "agent.config endpoint=%s build=%s active=%s AGENT_ENABLED=%s APP_ENV=%s "
        "is_dev=%s redis=%s inline=%s",
        endpoint,
        AGENT_API_BUILD,
        settings.agent_is_api_active,
        settings.agent_enabled,
        settings.app_env,
        settings.is_development_env,
        bool(settings.redis_url),
        settings.agent_inline_processing,
    )
    if settings.is_production_env and not settings.agent_enabled:
        logger.warning(
            "agent.config production with AGENT_ENABLED=false — Agent jobs may still be rejected elsewhere"
        )
    return settings
