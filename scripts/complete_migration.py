#!/usr/bin/env python3
"""
Complete migration: Knowledge Bases + Workflows/Apps

This script performs a complete migration:
1. Knowledge bases (datasets) with all documents and segments
2. Workflows/apps with all configurations

Usage:
    python scripts/complete_migration.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dify_migration import load_config_from_env, DifyMigration, logger


def complete_migration():
    """Migrate both knowledge bases and workflows/apps"""
    try:
        # Load configuration
        source_configs, target_config = load_config_from_env()

        logger.info(f"Configuration loaded: {len(source_configs)} source(s), 1 target")

        # Check if Console API credentials are available
        workflow_enabled = source_configs[0].email and target_config.email

        if not workflow_enabled:
            logger.warning("Console API credentials not configured!")
            logger.warning("Workflow migration will be skipped. Only knowledge bases will be migrated.")
            logger.info("To enable workflow migration, add SOURCE_EMAIL, SOURCE_PASSWORD, TARGET_EMAIL, TARGET_PASSWORD to .env")
            print()

            proceed = input("Continue with knowledge base migration only? (Y/n): ").strip().lower()
            if proceed in ['n', 'no']:
                logger.info("Migration cancelled")
                return

        # Ask for options
        skip_existing_input = input("Skip items that already exist in target? (Y/n): ").strip().lower()
        skip_existing = skip_existing_input not in ['n', 'no']

        auto_create_kb_input = input("Auto-create knowledge bases in target? (Y/n): ").strip().lower()
        auto_create_kb = auto_create_kb_input not in ['n', 'no']

        if workflow_enabled:
            include_secret_input = input("Include secret environment variables in apps? (y/N): ").strip().lower()
            include_secret = include_secret_input in ['y', 'yes']
        else:
            include_secret = False

        streaming_input = input("Use streaming mode (export→import per item)? (Y/n): ").strip().lower()
        streaming = streaming_input not in ['n', 'no']

        # Ask what to migrate
        if workflow_enabled:
            migrate_kb_input = input("Migrate knowledge bases? (Y/n): ").strip().lower()
            migrate_kb = migrate_kb_input not in ['n', 'no']

            migrate_apps_input = input("Migrate workflows/apps? (Y/n): ").strip().lower()
            migrate_apps = migrate_apps_input not in ['n', 'no']

            # Ask about parallel execution if both are enabled
            if migrate_kb and migrate_apps:
                parallel_input = input("Run KB and Workflow migrations in PARALLEL? (Y/n): ").strip().lower()
                parallel = parallel_input not in ['n', 'no']
            else:
                parallel = False
        else:
            migrate_kb = True
            migrate_apps = False
            parallel = False

        if not migrate_kb and not migrate_apps:
            logger.info("Nothing to migrate. Exiting.")
            return

        # Initialize migration
        migration = DifyMigration(source_configs, target_config)

        # Run complete migration
        logger.info("\n" + "="*80)
        logger.info("Starting Complete Migration")
        if migrate_kb and migrate_apps:
            logger.info(f"Phases: Knowledge Bases + Workflows/Apps ({'PARALLEL' if parallel else 'SEQUENTIAL'})")
        elif migrate_kb:
            logger.info("Phase: Knowledge Bases Only")
        else:
            logger.info("Phase: Workflows/Apps Only")
        logger.info("="*80 + "\n")

        migration.migrate_all_with_apps(
            skip_existing=skip_existing,
            auto_create_kb=auto_create_kb,
            include_secret=include_secret,
            streaming=streaming,
            migrate_datasets=migrate_kb,
            migrate_apps=migrate_apps,
            parallel=parallel
        )

        logger.info("\n" + "="*80)
        logger.info("Complete Migration Finished!")
        logger.info("="*80 + "\n")

    except Exception as error:
        logger.error(f"Migration failed: {str(error)}")
        logger.info("Check logs for more details: dify_migration.log")


if __name__ == '__main__':
    complete_migration()
