from __future__ import annotations

import argparse
import asyncio
import logging

from ..core.settings import get_settings
from ..services.dev_seed import initialize_dev_accounts

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize seeded accounts for FileFlash.")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Force reset seeded account passwords from the active environment configuration.",
    )
    return parser


async def run(reset_password: bool) -> int:
    settings = get_settings()
    if settings.is_production_env:
        logger.info(
            "Manual account initialization is using DEFAULT_ADMIN_* for APP_ENV=%s.",
            settings.app_env,
        )

    await initialize_dev_accounts(
        settings=settings,
        reset_password=reset_password,
        auto_run=False,
    )
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args()
    return asyncio.run(run(reset_password=args.reset_password))


if __name__ == "__main__":
    raise SystemExit(main())

