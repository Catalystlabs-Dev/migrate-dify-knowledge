#!/usr/bin/env python3
"""
Export all apps/workflows from source Dify instance(s)

This script exports all apps/workflows to YAML files in the export_data/ directory.
Each app is saved as app_{app_id}.yml

Usage:
    python scripts/export_apps.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dify_migration import load_config_from_env, DifyMigration, logger


def export_all_apps():
    """Export all apps from source instances"""
    try:
        # Load configuration
        source_configs, target_config = load_config_from_env()

        logger.info(f"Configuration loaded: {len(source_configs)} source(s)")

        # Check if Console API credentials are available
        if not source_configs[0].email:
            logger.error("Console API credentials not configured!")
            logger.error("Please add SOURCE_EMAIL and SOURCE_PASSWORD to .env file")
            return

        # Ask for include_secret option
        include_secret_input = input("Include secret environment variables? (y/N): ").strip().lower()
        include_secret = include_secret_input in ['y', 'yes']

        # Initialize migration
        migration = DifyMigration(source_configs, target_config)

        # Export all apps
        logger.info("\n" + "="*60)
        logger.info("Starting App Export")
        logger.info("="*60 + "\n")

        exported_apps = migration.export_all_apps(include_secret=include_secret)

        logger.info("\n" + "="*60)
        logger.info("Export Completed!")
        logger.info(f"Total apps exported: {len(exported_apps)}")
        logger.info(f"Export location: {migration.export_dir}")
        logger.info("="*60 + "\n")

        # Show exported files
        yml_files = list(migration.export_dir.glob('app_*.yml'))
        if yml_files:
            logger.info("Exported files:")
            for file in sorted(yml_files):
                logger.info(f"  - {file.name}")

    except Exception as error:
        logger.error(f"Export failed: {str(error)}")
        logger.info("Make sure .env file is configured with Console API credentials")


if __name__ == '__main__':
    export_all_apps()
