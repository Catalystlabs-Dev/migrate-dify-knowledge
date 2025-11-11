#!/usr/bin/env python3
"""
List all apps/workflows from source and target Dify instances

Usage:
    python scripts/list_apps.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dify_migration import load_config_from_env, DifyClient, logger


def list_all_apps():
    """List all apps from source and target instances"""
    try:
        # Load configuration
        source_configs, target_config = load_config_from_env()

        logger.info(f"Configuration loaded: {len(source_configs)} source(s), 1 target")

        # Check if Console API credentials are available
        if not source_configs[0].email or not target_config.email:
            logger.error("Console API credentials not configured!")
            logger.error("Please add SOURCE_EMAIL, SOURCE_PASSWORD, TARGET_EMAIL, TARGET_PASSWORD to .env file")
            return

        # List apps from each source
        for i, config in enumerate(source_configs, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Source {i}/{len(source_configs)}")
            logger.info(f"{'='*60}")

            try:
                client = DifyClient(config)
                apps = client.get_all_apps()

                logger.info(f"Found {len(apps)} apps/workflows:")
                logger.info(f"\n{'No.':<5} {'Name':<40} {'Mode':<15} {'Updated'}")
                logger.info("-" * 80)

                for idx, app in enumerate(apps, 1):
                    name = app.get('name', 'Unknown')[:38]
                    mode = app.get('mode', 'N/A').upper()
                    updated = app.get('updated_at', 'N/A')[:19].replace('T', ' ')
                    logger.info(f"{idx:<5} {name:<40} {mode:<15} {updated}")

            except Exception as error:
                logger.error(f"Failed to list apps from source {i}: {str(error)}")

        # List apps from target
        logger.info(f"\n{'='*60}")
        logger.info(f"Target")
        logger.info(f"{'='*60}")

        try:
            target_client = DifyClient(target_config)
            apps = target_client.get_all_apps()

            logger.info(f"Found {len(apps)} apps/workflows:")
            logger.info(f"\n{'No.':<5} {'Name':<40} {'Mode':<15} {'Updated'}")
            logger.info("-" * 80)

            for idx, app in enumerate(apps, 1):
                name = app.get('name', 'Unknown')[:38]
                mode = app.get('mode', 'N/A').upper()
                updated = app.get('updated_at', 'N/A')[:19].replace('T', ' ')
                logger.info(f"{idx:<5} {name:<40} {mode:<15} {updated}")

        except Exception as error:
            logger.error(f"Failed to list apps from target: {str(error)}")

        logger.info(f"\n{'='*60}\n")

    except Exception as error:
        logger.error(f"Failed to load configuration: {str(error)}")
        logger.info("Make sure .env file is configured with Console API credentials")


if __name__ == '__main__':
    list_all_apps()
