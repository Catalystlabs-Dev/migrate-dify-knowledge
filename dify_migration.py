"""
Dify Knowledge Base and Workflow Migration Tool

Migrates knowledge bases (datasets) and workflows/apps from one Dify instance to another,
including all documents, chunks, segments, metadata, and DSL configurations.

This module provides the core DifyClient and DifyMigration classes for performing
migrations in both streaming and batch modes, with support for parallel execution.
"""

import os
import json
from typing import Dict, List, Optional
from pathlib import Path
import time
import threading
from dotenv import load_dotenv

# Import from modular components
from config import DifyConfig
from dify_client import DifyClient
from logger_utils import setup_logging


# Initialize thread-safe logger
logger = setup_logging(
    log_file='dify_migration.log',
    include_thread_name=True
)


class DifyMigration:
    """Main migration class for transferring knowledge bases between Dify instances"""

    def __init__(self, source_configs: List[DifyConfig], target_config: DifyConfig):
        """
        Initialize migration tool

        @param source_configs - List of configurations for source Dify instances (supports multiple API keys)
        @param target_config - Configuration for target Dify instance
        """
        self.source_clients = [DifyClient(config) for config in source_configs]
        self.target_client = DifyClient(target_config)
        self.export_dir = Path('export_data')
        self.export_dir.mkdir(exist_ok=True)
        logger.info(f"Initialized migration with {len(self.source_clients)} source(s) and 1 target")

    def export_dataset(self, dataset_id: str, source_client: DifyClient) -> Dict:
        """
        Export a single dataset with all its documents and segments

        @param dataset_id - ID of the dataset to export
        @param source_client - DifyClient instance to use for export
        @returns Dictionary containing dataset metadata and all documents
        """
        logger.info(f"Exporting dataset {dataset_id}")

        # Get all datasets to find the one we want
        all_datasets = source_client.get_all_datasets()
        dataset = next((ds for ds in all_datasets if ds['id'] == dataset_id), None)

        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Get all documents
        documents = source_client.get_all_documents(dataset_id)

        # Get segments for each document
        for document in documents:
            document_id = document['id']
            segments = source_client.get_document_segments(dataset_id, document_id)
            document['segments'] = segments

        export_data = {
            'dataset': dataset,
            'documents': documents
        }

        # Save to file
        export_file = self.export_dir / f"dataset_{dataset_id}.json"
        with open(export_file, 'w', encoding='utf-8') as file:
            json.dump(export_data, file, indent=2, ensure_ascii=False)

        logger.info(f"Dataset exported to {export_file}")
        return export_data

    def export_all_datasets(self) -> List[Dict]:
        """
        Export all datasets from all source instances

        @returns List of exported dataset data from all sources
        """
        logger.info("Exporting all datasets from all sources")
        all_exported_data = []

        for index, source_client in enumerate(self.source_clients, 1):
            logger.info(f"Processing source {index}/{len(self.source_clients)}")

            try:
                all_datasets = source_client.get_all_datasets()
                logger.info(f"Found {len(all_datasets)} datasets in source {index}")

                for dataset in all_datasets:
                    try:
                        data = self.export_dataset(dataset['id'], source_client)
                        all_exported_data.append(data)
                    except Exception as error:
                        logger.error(f"Failed to export dataset {dataset['id']} from source {index}: {str(error)}")

            except Exception as error:
                logger.error(f"Failed to access source {index}: {str(error)}")

        logger.info(f"Exported {len(all_exported_data)} datasets in total from all sources")
        return all_exported_data

    def import_dataset(self, export_data: Dict, skip_existing: bool = True, auto_create: bool = True) -> Optional[str]:
        """
        Import a dataset to target instance (auto-creates knowledge base)

        @param export_data - Exported dataset data
        @param skip_existing - Skip if dataset with same name exists
        @param auto_create - Automatically create knowledge base in target (default: True)
        @returns ID of created dataset or None if skipped
        """
        dataset_info = export_data['dataset']
        dataset_name = dataset_info['name']

        logger.info(f"Importing dataset: {dataset_name}")

        # Check if dataset already exists
        existing_datasets = self.target_client.get_all_datasets()
        existing_dataset = next((ds for ds in existing_datasets if ds['name'] == dataset_name), None)

        if existing_dataset:
            if skip_existing:
                logger.warning(f"Dataset '{dataset_name}' already exists, skipping")
                return None
            else:
                logger.info(f"Dataset '{dataset_name}' already exists, using existing dataset ID: {existing_dataset['id']}")
                new_dataset_id = existing_dataset['id']
        else:
            # Auto-create knowledge base in target
            if auto_create:
                logger.info(f"Auto-creating knowledge base: {dataset_name}")
                new_dataset = self.target_client.create_dataset(
                    name=dataset_name,
                    description=dataset_info.get('description', '')
                )
                new_dataset_id = new_dataset['id']
                logger.info(f"Knowledge base '{dataset_name}' created with ID: {new_dataset_id}")
            else:
                logger.error(f"Dataset '{dataset_name}' does not exist and auto_create is disabled")
                return None

        # Import documents
        documents = export_data['documents']
        logger.info(f"Importing {len(documents)} documents to dataset '{dataset_name}'")

        success_count = 0
        for idx, document in enumerate(documents, 1):
            try:
                logger.info(f"  Importing document {idx}/{len(documents)}: {document.get('name')}")
                self._import_document(new_dataset_id, document)
                success_count += 1

                # Add delay between document imports to avoid rate limiting and server overload
                # Increased to 3 seconds to prevent 500 errors from server
                if idx < len(documents):  # Don't delay after last document
                    logger.debug(f"  Waiting 3 seconds before next document...")
                    time.sleep(3)

            except Exception as error:
                logger.error(f"Failed to import document {document.get('name')}: {str(error)}")

        logger.info(f"Dataset '{dataset_name}' imported successfully: {success_count}/{len(documents)} documents")
        return new_dataset_id

    def _import_document(self, dataset_id: str, document_data: Dict) -> None:
        """
        Import a single document with its segments

        @param dataset_id - ID of the target dataset
        @param document_data - Document data including segments
        """
        document_name = document_data['name']
        segments = document_data.get('segments', [])

        logger.info(f"Importing document: {document_name} with {len(segments)} segments")

        # Combine all segment content into single text
        combined_text = "\n\n".join([seg['content'] for seg in segments if 'content' in seg])

        if not combined_text:
            logger.warning(f"Document {document_name} has no content, skipping")
            return

        # Create document
        self.target_client.create_document_by_text(
            dataset_id=dataset_id,
            name=document_name,
            text=combined_text
        )

        # Wait for indexing to complete
        logger.info(f"Document {document_name} created, waiting for indexing...")
        time.sleep(3)

    def import_from_file(self, export_file_path: str, skip_existing: bool = True) -> None:
        """
        Import dataset from exported JSON file

        @param export_file_path - Path to exported JSON file
        @param skip_existing - Skip if dataset already exists
        """
        logger.info(f"Importing from file: {export_file_path}")

        with open(export_file_path, 'r', encoding='utf-8') as file:
            export_data = json.load(file)

        self.import_dataset(export_data, skip_existing)

    def migrate_all(self, skip_existing: bool = True, auto_create: bool = True, streaming: bool = True) -> None:
        """
        Complete migration: export from all sources and import to target

        @param skip_existing - Skip datasets that already exist in target
        @param auto_create - Automatically create knowledge bases in target (default: True)
        @param streaming - Stream migration (export->import per dataset) instead of batch (default: True)
        """
        logger.info("Starting full migration from all sources")
        logger.info(f"Mode: {'Streaming' if streaming else 'Batch'} migration")

        if streaming:
            # NEW: Streaming mode - export and import one by one
            self._migrate_streaming(skip_existing, auto_create)
        else:
            # OLD: Batch mode - export all first, then import all
            self._migrate_batch(skip_existing, auto_create)

    def _migrate_streaming(self, skip_existing: bool, auto_create: bool) -> None:
        """
        Streaming migration: export->import one dataset at a time
        More memory efficient and provides real-time feedback
        """
        success_count = 0
        skipped_count = 0
        failed_count = 0
        total_count = 0

        # Get already imported datasets to track progress
        try:
            existing_datasets = self.target_client.get_all_datasets()
            existing_names = {ds['name'] for ds in existing_datasets}
            logger.info(f"Found {len(existing_names)} existing datasets in target")
        except Exception as e:
            logger.warning(f"Could not fetch existing datasets: {e}")
            existing_names = set()

        # Process each source
        for source_idx, source_client in enumerate(self.source_clients, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing Source {source_idx}/{len(self.source_clients)}")
            logger.info(f"{'='*60}")

            try:
                all_datasets = source_client.get_all_datasets()
                logger.info(f"Found {len(all_datasets)} datasets in source {source_idx}")

                # Process each dataset immediately
                for dataset in all_datasets:
                    total_count += 1
                    dataset_name = dataset['name']

                    logger.info(f"\n[{total_count}] Processing: {dataset_name}")

                    # Check if already processed (in existing names)
                    if skip_existing and dataset_name in existing_names:
                        logger.info(f"  ⏭️  Already exists in target, skipping")
                        skipped_count += 1
                        continue

                    try:
                        # Export this dataset
                        logger.info(f"  📤 Exporting...")
                        export_data = self.export_dataset(dataset['id'], source_client)

                        # Import immediately
                        logger.info(f"  📥 Importing...")
                        result = self.import_dataset(export_data, skip_existing=False, auto_create=auto_create)

                        if result:
                            logger.info(f"  ✅ Success!")
                            success_count += 1
                            existing_names.add(dataset_name)  # Track as imported
                        else:
                            logger.warning(f"  ⏭️  Skipped (already exists)")
                            skipped_count += 1

                    except Exception as error:
                        logger.error(f"  ❌ Failed: {str(error)}")
                        failed_count += 1

            except Exception as error:
                logger.error(f"Failed to access source {source_idx}: {str(error)}")

        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("Streaming Migration Completed!")
        logger.info(f"Total datasets processed: {total_count}")
        logger.info(f"Successfully imported: {success_count}")
        logger.info(f"Skipped (already exists): {skipped_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"{'='*60}\n")

    def _migrate_batch(self, skip_existing: bool, auto_create: bool) -> None:
        """
        Batch migration: export all first, then import all
        Original behavior - kept for compatibility
        """
        # Export all datasets from all sources
        exported_data = self.export_all_datasets()

        logger.info(f"Starting import of {len(exported_data)} datasets to target")

        # Import to target with statistics
        success_count = 0
        skipped_count = 0
        failed_count = 0

        for dataset_data in exported_data:
            dataset_name = dataset_data['dataset'].get('name', 'unknown')
            try:
                result = self.import_dataset(dataset_data, skip_existing, auto_create)
                if result is None:
                    skipped_count += 1
                else:
                    success_count += 1
            except Exception as error:
                logger.error(f"Failed to import dataset '{dataset_name}': {str(error)}")
                failed_count += 1

        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("Batch Migration Completed!")
        logger.info(f"Total datasets processed: {len(exported_data)}")
        logger.info(f"Successfully imported: {success_count}")
        logger.info(f"Skipped (already exists): {skipped_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"{'='*60}\n")

    # ========================================
    # Workflow/App Migration Methods
    # ========================================

    def export_app(self, app_id: str, source_client: DifyClient, include_secret: bool = False) -> Dict:
        """
        Export a single app/workflow with its DSL

        @param app_id - ID of the app to export
        @param source_client - DifyClient instance to use for export
        @param include_secret - Include secret environment variables
        @returns Dictionary containing app metadata and DSL content
        """
        logger.info(f"Exporting app {app_id}")

        # Get app info
        all_apps = source_client.get_all_apps()
        app = next((a for a in all_apps if a['id'] == app_id), None)

        if not app:
            raise ValueError(f"App {app_id} not found")

        # Export DSL
        dsl_content = source_client.export_app_dsl(app_id, include_secret=include_secret)

        export_data = {
            'app': app,
            'dsl_content': dsl_content
        }

        # Save to file
        export_file = self.export_dir / f"app_{app_id}.yml"
        with open(export_file, 'w', encoding='utf-8') as file:
            file.write(dsl_content)

        logger.info(f"App exported to {export_file}")
        return export_data

    def export_all_apps(self, include_secret: bool = False) -> List[Dict]:
        """
        Export all apps/workflows from all source instances

        @param include_secret - Include secret environment variables
        @returns List of exported app data from all sources
        """
        logger.info("Exporting all apps from all sources")
        all_exported_apps = []

        for index, source_client in enumerate(self.source_clients, 1):
            logger.info(f"Processing source {index}/{len(self.source_clients)}")

            try:
                all_apps = source_client.get_all_apps()
                logger.info(f"Found {len(all_apps)} apps in source {index}")

                for app in all_apps:
                    try:
                        data = self.export_app(app['id'], source_client, include_secret=include_secret)
                        all_exported_apps.append(data)
                    except Exception as error:
                        logger.error(f"Failed to export app {app['id']} from source {index}: {str(error)}")

            except Exception as error:
                logger.error(f"Failed to access source {index}: {str(error)}")

        logger.info(f"Exported {len(all_exported_apps)} apps in total from all sources")
        return all_exported_apps

    def import_app(self, export_data: Dict, skip_existing: bool = True) -> Optional[str]:
        """
        Import an app/workflow to target instance

        @param export_data - Exported app data with DSL content
        @param skip_existing - Skip if app with same name exists
        @returns ID of imported app or None if skipped
        """
        app_info = export_data['app']
        app_name = app_info['name']
        dsl_content = export_data['dsl_content']

        logger.info(f"Importing app: {app_name}")

        # Check if app already exists
        existing_apps = self.target_client.get_all_apps()
        existing_app = next((a for a in existing_apps if a['name'] == app_name), None)

        if existing_app:
            if skip_existing:
                logger.warning(f"App '{app_name}' already exists, skipping")
                return None
            else:
                logger.warning(f"App '{app_name}' already exists, will create duplicate")

        try:
            # Import app
            result = self.target_client.import_app_dsl(
                yaml_content=dsl_content,
                name=None,  # Use name from DSL
                description=None  # Use description from DSL
            )

            imported_app = result.get('data', {}).get('app', {})
            app_id = imported_app.get('id')

            logger.info(f"App '{app_name}' imported successfully with ID: {app_id}")
            return app_id

        except Exception as error:
            logger.error(f"Failed to import app '{app_name}': {str(error)}")
            raise

    def import_app_from_file(self, dsl_file_path: str, skip_existing: bool = True) -> Optional[str]:
        """
        Import app from exported DSL file

        @param dsl_file_path - Path to DSL YAML file
        @param skip_existing - Skip if app already exists
        @returns ID of imported app or None if skipped
        """
        logger.info(f"Importing app from file: {dsl_file_path}")

        with open(dsl_file_path, 'r', encoding='utf-8') as file:
            dsl_content = file.read()

        # Parse YAML to get app name (for duplicate check)
        import yaml
        try:
            dsl_data = yaml.safe_load(dsl_content)
            app_name = dsl_data.get('name', 'Unknown')
        except Exception:
            app_name = 'Unknown'

        export_data = {
            'app': {'name': app_name},
            'dsl_content': dsl_content
        }

        return self.import_app(export_data, skip_existing)

    def migrate_all_apps(self, skip_existing: bool = True, include_secret: bool = False, streaming: bool = True) -> None:
        """
        Complete app/workflow migration: export from all sources and import to target

        @param skip_existing - Skip apps that already exist in target
        @param include_secret - Include secret environment variables in export
        @param streaming - Stream migration (export->import per app) instead of batch (default: True)
        """
        logger.info("Starting full app/workflow migration from all sources")
        logger.info(f"Mode: {'Streaming' if streaming else 'Batch'} migration")

        if streaming:
            self._migrate_apps_streaming(skip_existing, include_secret)
        else:
            self._migrate_apps_batch(skip_existing, include_secret)

    def _migrate_apps_streaming(self, skip_existing: bool, include_secret: bool) -> None:
        """
        Streaming migration for apps: export->import one app at a time
        """
        success_count = 0
        skipped_count = 0
        failed_count = 0
        total_count = 0

        # Get existing apps in target
        try:
            existing_apps = self.target_client.get_all_apps()
            existing_names = {app['name'] for app in existing_apps}
            logger.info(f"Found {len(existing_names)} existing apps in target")
        except Exception as e:
            logger.warning(f"Could not fetch existing apps: {e}")
            existing_names = set()

        # Process each source
        for source_idx, source_client in enumerate(self.source_clients, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing Source {source_idx}/{len(self.source_clients)}")
            logger.info(f"{'='*60}")

            try:
                all_apps = source_client.get_all_apps()
                logger.info(f"Found {len(all_apps)} apps in source {source_idx}")

                # Process each app immediately
                for app in all_apps:
                    total_count += 1
                    app_name = app['name']

                    logger.info(f"\n[{total_count}] Processing: {app_name}")

                    # Check if already exists
                    if skip_existing and app_name in existing_names:
                        logger.info(f"  ⏭️  Already exists in target, skipping")
                        skipped_count += 1
                        continue

                    try:
                        # Export this app
                        logger.info(f"  📤 Exporting...")
                        export_data = self.export_app(app['id'], source_client, include_secret=include_secret)

                        # Import immediately
                        logger.info(f"  📥 Importing...")
                        result = self.import_app(export_data, skip_existing=False)

                        if result:
                            logger.info(f"  ✅ Success!")
                            success_count += 1
                            existing_names.add(app_name)
                        else:
                            logger.warning(f"  ⏭️  Skipped (already exists)")
                            skipped_count += 1

                    except Exception as error:
                        logger.error(f"  ❌ Failed: {str(error)}")
                        failed_count += 1

            except Exception as error:
                logger.error(f"Failed to access source {source_idx}: {str(error)}")

        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("Streaming App Migration Completed!")
        logger.info(f"Total apps processed: {total_count}")
        logger.info(f"Successfully imported: {success_count}")
        logger.info(f"Skipped (already exists): {skipped_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"{'='*60}\n")

    def _migrate_apps_batch(self, skip_existing: bool, include_secret: bool) -> None:
        """
        Batch migration for apps: export all first, then import all
        """
        # Export all apps from all sources
        exported_apps = self.export_all_apps(include_secret=include_secret)

        logger.info(f"Starting import of {len(exported_apps)} apps to target")

        # Import to target with statistics
        success_count = 0
        skipped_count = 0
        failed_count = 0

        for app_data in exported_apps:
            app_name = app_data['app'].get('name', 'unknown')
            try:
                result = self.import_app(app_data, skip_existing)
                if result is None:
                    skipped_count += 1
                else:
                    success_count += 1
            except Exception as error:
                logger.error(f"Failed to import app '{app_name}': {str(error)}")
                failed_count += 1

        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("Batch App Migration Completed!")
        logger.info(f"Total apps processed: {len(exported_apps)}")
        logger.info(f"Successfully imported: {success_count}")
        logger.info(f"Skipped (already exists): {skipped_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"{'='*60}\n")

    def migrate_all_with_apps(
        self,
        skip_existing: bool = True,
        auto_create_kb: bool = True,
        include_secret: bool = False,
        streaming: bool = True,
        migrate_datasets: bool = True,
        migrate_apps: bool = True,
        parallel: bool = True
    ) -> None:
        """
        Complete migration: knowledge bases AND apps/workflows

        @param skip_existing - Skip items that already exist in target
        @param auto_create_kb - Automatically create knowledge bases in target
        @param include_secret - Include secret environment variables in app export
        @param streaming - Stream migration (export->import per item) instead of batch
        @param migrate_datasets - Migrate knowledge bases (default: True)
        @param migrate_apps - Migrate apps/workflows (default: True)
        @param parallel - Run KB and Workflow migrations in parallel (default: True)
        """
        logger.info("="*80)
        logger.info("COMPLETE MIGRATION: Knowledge Bases + Apps/Workflows")
        logger.info(f"Execution Mode: {'PARALLEL' if parallel else 'SEQUENTIAL'}")
        logger.info("="*80)

        if parallel and migrate_datasets and migrate_apps:
            # Parallel execution - both migrations run simultaneously
            logger.info("\n🚀 Starting PARALLEL migration (KB + Workflows running together)...\n")

            kb_error = None
            workflow_error = None

            def run_kb_migration():
                nonlocal kb_error
                try:
                    logger.info(">>> THREAD 1: Migrating Knowledge Bases <<<")
                    self.migrate_all(skip_existing=skip_existing, auto_create=auto_create_kb, streaming=streaming)
                except Exception as error:
                    kb_error = error
                    logger.error(f"Knowledge base migration failed: {str(error)}")

            def run_workflow_migration():
                nonlocal workflow_error
                try:
                    logger.info(">>> THREAD 2: Migrating Apps/Workflows <<<")
                    self.migrate_all_apps(skip_existing=skip_existing, include_secret=include_secret, streaming=streaming)
                except Exception as error:
                    workflow_error = error
                    logger.error(f"App migration failed: {str(error)}")

            # Create and start threads
            kb_thread = threading.Thread(target=run_kb_migration, name="KB-Migration")
            workflow_thread = threading.Thread(target=run_workflow_migration, name="Workflow-Migration")

            kb_thread.start()
            workflow_thread.start()

            # Wait for both to complete
            kb_thread.join()
            workflow_thread.join()

            # Report results
            logger.info("\n" + "="*80)
            logger.info("PARALLEL MIGRATION RESULTS:")
            if kb_error:
                logger.error(f"  ❌ Knowledge Bases: FAILED - {str(kb_error)}")
            else:
                logger.info("  ✅ Knowledge Bases: SUCCESS")

            if workflow_error:
                logger.error(f"  ❌ Workflows/Apps: FAILED - {str(workflow_error)}")
            else:
                logger.info("  ✅ Workflows/Apps: SUCCESS")
            logger.info("="*80)

        else:
            # Sequential execution - original behavior
            logger.info("\n🔄 Starting SEQUENTIAL migration...\n")

            if migrate_datasets:
                logger.info("\n>>> PHASE 1: Migrating Knowledge Bases <<<\n")
                try:
                    self.migrate_all(skip_existing=skip_existing, auto_create=auto_create_kb, streaming=streaming)
                except Exception as error:
                    logger.error(f"Knowledge base migration failed: {str(error)}")

            if migrate_apps:
                logger.info("\n>>> PHASE 2: Migrating Apps/Workflows <<<\n")
                try:
                    self.migrate_all_apps(skip_existing=skip_existing, include_secret=include_secret, streaming=streaming)
                except Exception as error:
                    logger.error(f"App migration failed: {str(error)}")

            logger.info("\n" + "="*80)
            logger.info("SEQUENTIAL MIGRATION FINISHED!")
            logger.info("="*80)


def load_config_from_env() -> tuple[List[DifyConfig], DifyConfig]:
    """
    Load configuration from .env file
    Supports multiple source API keys separated by comma
    Supports optional email/password for Console API (workflow migration)

    @returns Tuple of (list_of_source_configs, target_config)
    @throws ValueError - If required environment variables are missing
    """
    load_dotenv()

    source_base_url = os.getenv('SOURCE_BASE_URL')
    source_api_keys_raw = os.getenv('SOURCE_API_KEYS')  # Support multiple keys
    target_base_url = os.getenv('TARGET_BASE_URL')
    target_api_key = os.getenv('TARGET_API_KEY')

    # Optional: Console API credentials for workflow migration
    source_email = os.getenv('SOURCE_EMAIL')
    source_password = os.getenv('SOURCE_PASSWORD')
    target_email = os.getenv('TARGET_EMAIL')
    target_password = os.getenv('TARGET_PASSWORD')

    # Fallback to single key for backwards compatibility
    if not source_api_keys_raw:
        source_api_keys_raw = os.getenv('SOURCE_API_KEY')

    if not all([source_base_url, source_api_keys_raw, target_base_url, target_api_key]):
        missing = []
        if not source_base_url:
            missing.append('SOURCE_BASE_URL')
        if not source_api_keys_raw:
            missing.append('SOURCE_API_KEYS (or SOURCE_API_KEY)')
        if not target_base_url:
            missing.append('TARGET_BASE_URL')
        if not target_api_key:
            missing.append('TARGET_API_KEY')

        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    # Parse multiple API keys (comma-separated)
    source_api_keys = [key.strip() for key in source_api_keys_raw.split(',') if key.strip()]

    if not source_api_keys:
        raise ValueError("No valid SOURCE_API_KEYS found")

    # Create config for each source API key
    source_configs = []
    for api_key in source_api_keys:
        source_configs.append(DifyConfig(
            base_url=source_base_url,
            api_key=api_key,
            email=source_email,
            password=source_password
        ))

    target_config = DifyConfig(
        base_url=target_base_url,
        api_key=target_api_key,
        email=target_email,
        password=target_password
    )

    logger.info(f"Loaded configuration: {len(source_configs)} source(s), 1 target")
    if source_email and target_email:
        logger.info("Console API credentials loaded (workflow migration enabled)")
    return source_configs, target_config


def load_config_from_json() -> tuple[List[DifyConfig], DifyConfig]:
    """
    Load configuration from config.json file
    Supports both single and multiple source API keys

    @returns Tuple of (list_of_source_configs, target_config)
    @throws FileNotFoundError - If config.json not found
    """
    config_file = Path('config.json')

    if not config_file.exists():
        raise FileNotFoundError("config.json not found")

    with open(config_file, 'r') as file:
        config = json.load(file)

    source_configs = []

    # Support both single source and multiple sources
    if 'source' in config:
        # Single source (backwards compatible)
        source_configs.append(DifyConfig(
            base_url=config['source']['base_url'],
            api_key=config['source']['api_key']
        ))
    elif 'sources' in config:
        # Multiple sources
        for source in config['sources']:
            source_configs.append(DifyConfig(
                base_url=source['base_url'],
                api_key=source['api_key']
            ))
    else:
        raise ValueError("config.json must contain either 'source' or 'sources' key")

    target_config = DifyConfig(
        base_url=config['target']['base_url'],
        api_key=config['target']['api_key']
    )

    logger.info(f"Loaded configuration: {len(source_configs)} source(s), 1 target")
    return source_configs, target_config


def main():
    """
    Main function - example usage

    Configure your source and target Dify instances in .env or config.json
    Priority: .env file > config.json
    Supports multiple source API keys
    """
    try:
        # Try loading from .env first
        logger.info("Loading configuration from .env file...")
        source_configs, target_config = load_config_from_env()
    except (ValueError, FileNotFoundError) as env_error:
        logger.warning(f"Failed to load from .env: {str(env_error)}")

        try:
            # Fallback to config.json
            logger.info("Trying config.json as fallback...")
            source_configs, target_config = load_config_from_json()
        except FileNotFoundError:
            logger.error("No configuration found!")
            logger.info("Please create either:")
            logger.info("  1. .env file (recommended) - see .env.example")
            logger.info("  2. config.json - see config.example.json")
            return

    # Initialize migration with multiple sources
    migration = DifyMigration(source_configs, target_config)

    # Run migration with streaming enabled (export->import per dataset)
    # streaming=True: More memory efficient, real-time feedback, prevents duplicates
    # streaming=False: Batch mode (old behavior)
    migration.migrate_all(skip_existing=True, auto_create=True, streaming=True)


if __name__ == '__main__':
    main()
