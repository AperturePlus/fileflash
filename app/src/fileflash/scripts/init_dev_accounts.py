from __future__ import annotations

import argparse
import asyncio
import logging

from ..core.settings import get_settings
from ..services.dev_seed import initialize_dev_accounts

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize development test accounts for FileFlash.")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Force reset passwords to defaults (admin/admin123, demo/demo123).",
    )
    return parser


async def run(reset_password: bool) -> int:
    settings = get_settings()
    if settings.is_production_env:
        logger.warning(
            "Manual dev-account initialization is running under APP_ENV=%s. This is not executed automatically in production.",
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

