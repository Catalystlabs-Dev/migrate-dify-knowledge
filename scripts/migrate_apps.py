#!/usr/bin/env python3
"""
Migrate apps/workflows from source to target Dify instance(s)

This script performs a complete workflow migration:
1. Exports all workflows/apps from source(s)
2. Imports them to target

Usage:
    python scripts/migrate_apps.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dify_migration import load_config_from_env, DifyMigration, logger


def migrate_workflows():
    """Migrate all workflows/apps from source to target"""
    try:
        # Load configuration
        source_configs, target_config = load_config_from_env()

        logger.info(f"Configuration loaded: {len(source_configs)} source(s), 1 target")

        # Check if Console API credentials are available
        if not source_configs[0].email or not target_config.email:
            logger.error("Console API credentials not configured!")
            logger.error("Please add SOURCE_EMAIL, SOURCE_PASSWORD, TARGET_EMAIL, TARGET_PASSWORD to .env file")
            return

        # Ask for options
        skip_existing_input = input("Skip apps that already exist in target? (Y/n): ").strip().lower()
        skip_existing = skip_existing_input not in ['n', 'no']

        include_secret_input = input("Include secret environment variables? (y/N): ").strip().lower()
        include_secret = include_secret_input in ['y', 'yes']

        streaming_input = input("Use streaming mode (export→import per app)? (Y/n): ").strip().lower()
        streaming = streaming_input not in ['n', 'no']

        # Initialize migration
        migration = DifyMigration(source_configs, target_config)

        # Run migration
        logger.info("\n" + "="*80)
        logger.info("Starting Workflow/App Migration")
        logger.info("="*80 + "\n")

        migration.migrate_all_apps(
            skip_existing=skip_existing,
            include_secret=include_secret,
            streaming=streaming
        )

        logger.info("\n" + "="*80)
        logger.info("Migration Completed!")
        logger.info("="*80 + "\n")

    except Exception as error:
        logger.error(f"Migration failed: {str(error)}")
        logger.info("Check logs for more details: dify_migration.log")


if __name__ == '__main__':
    migrate_workflows()
