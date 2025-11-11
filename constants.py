"""
Dify Migration Tool - Constants and Configuration

Centralized constants for API endpoints, default values, and enumerations.
"""

from enum import Enum


class APIEndpoints:
    """API endpoint paths for Dify instances"""

    # Knowledge Base API (v1)
    DATASETS = '/v1/datasets'
    DATASET_DETAIL = '/v1/datasets/{dataset_id}'
    DOCUMENTS = '/v1/datasets/{dataset_id}/documents'
    DOCUMENT_DETAIL = '/v1/datasets/{dataset_id}/documents/{document_id}'
    SEGMENTS = '/v1/datasets/{dataset_id}/documents/{document_id}/segments'
    CREATE_BY_TEXT = '/v1/datasets/{dataset_id}/document/create_by_text'

    # Console API (internal)
    CONSOLE_LOGIN = '/console/api/login'
    CONSOLE_APPS = '/console/api/apps'
    CONSOLE_APP_DETAIL = '/console/api/apps/{app_id}'
    CONSOLE_APP_EXPORT = '/console/api/apps/{app_id}/export'
    CONSOLE_APP_IMPORT = '/console/api/apps/imports'


class MigrationDefaults:
    """Default values for migration operations"""

    # Pagination
    PAGE_SIZE = 20
    APPS_PAGE_SIZE = 30

    # Timeouts
    REQUEST_TIMEOUT = 30  # seconds
    IMPORT_TIMEOUT = 60   # seconds

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2.0  # seconds

    # Rate limiting
    RATE_LIMIT_DELAY = 0.5      # seconds between requests
    DOCUMENT_DELAY = 3.0         # seconds between document imports
    INDEXING_DELAY = 3.0         # seconds to wait for indexing

    # Export
    EXPORT_DIRECTORY = 'export_data'


class MigrationMode(Enum):
    """Migration execution modes"""
    STREAMING = "streaming"  # Export→Import one by one
    BATCH = "batch"          # Export all, then import all


class ExecutionMode(Enum):
    """Parallel vs Sequential execution"""
    PARALLEL = "parallel"      # KB + Workflows run simultaneously
    SEQUENTIAL = "sequential"  # KB first, then Workflows


class ImportStatus(Enum):
    """Import operation status"""
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


class MigrationPhase(Enum):
    """Migration phases for logging"""
    EXPORT = "export"
    IMPORT = "import"
    VALIDATE = "validate"
    COMPLETE = "complete"
