"""
Dify Knowledge Base Migration Tool

This script migrates knowledge bases (datasets) from one Dify instance to another,
including all documents, chunks, and metadata.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import time
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dify_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class DifyConfig:
    """Configuration for Dify instance"""
    base_url: str
    api_key: str

    def __post_init__(self):
        # Remove trailing slash from base_url if present
        self.base_url = self.base_url.rstrip('/')


class DifyClient:
    """Client for interacting with Dify API"""

    def __init__(self, config: DifyConfig):
        """
        Initialize Dify client

        @param config - DifyConfig object with base_url and api_key
        """
        self.config = config
        self.headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Dict:
        """
        Make HTTP request to Dify API with retry logic for 500 errors

        @param method - HTTP method (GET, POST, DELETE, etc.)
        @param endpoint - API endpoint path
        @param data - Request body data (dict)
        @param files - Files to upload (dict)
        @param params - Query parameters (dict)
        @param max_retries - Maximum number of retries for 500 errors (default: 3)
        @param retry_delay - Initial delay between retries in seconds (default: 2.0)
        @returns API response as dictionary
        @throws requests.exceptions.RequestException - On request failure after all retries
        """
        url = f"{self.config.base_url}{endpoint}"
        headers = self.headers.copy()

        # Remove Content-Type for file uploads
        if files:
            headers.pop('Content-Type', None)

        # Retry logic for 500 errors
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if not files else None,
                    files=files,
                    params=params,
                    timeout=30,
                    verify=True  # Keep SSL verification enabled but handle cert issues
                )
                response.raise_for_status()

                # Add small delay to avoid rate limiting (0.5 seconds between requests)
                time.sleep(0.5)

                return response.json() if response.content else {}

            except requests.exceptions.SSLError as ssl_error:
                logger.error(f"SSL Certificate error: {str(ssl_error)}")
                logger.warning("Retrying with SSL verification disabled (not recommended for production)")
                try:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data if not files else None,
                        files=files,
                        params=params,
                        timeout=30,
                        verify=False  # Disable SSL verification as fallback
                    )
                    response.raise_for_status()
                    time.sleep(0.5)
                    return response.json() if response.content else {}
                except requests.exceptions.RequestException as retry_error:
                    logger.error(f"Retry failed: {str(retry_error)}")
                    raise

            except requests.exceptions.HTTPError as http_error:
                # Check if it's a 500 error
                if hasattr(http_error, 'response') and http_error.response is not None:
                    status_code = http_error.response.status_code

                    # Retry only on 500 Internal Server Error
                    if status_code == 500 and attempt < max_retries:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"500 Server Error on attempt {attempt + 1}/{max_retries + 1}. "
                            f"Retrying in {wait_time:.1f} seconds..."
                        )
                        time.sleep(wait_time)
                        last_error = http_error
                        continue
                    else:
                        # Log and raise for other errors or after max retries
                        logger.error(f"Request failed: {method} {url} - {str(http_error)}")
                        logger.error(f"Response: {http_error.response.text}")
                        raise
                else:
                    raise

            except requests.exceptions.RequestException as error:
                logger.error(f"Request failed: {method} {url} - {str(error)}")
                if hasattr(error, 'response') and error.response is not None:
                    logger.error(f"Response: {error.response.text}")
                raise

        # If we exhausted all retries
        if last_error:
            logger.error(f"Failed after {max_retries + 1} attempts")
            raise last_error

        # Should never reach here, but just in case
        raise requests.exceptions.RequestException("Request failed unexpectedly")

    def list_datasets(self, page: int = 1, limit: int = 20) -> Dict:
        """
        List all knowledge bases (datasets)

        @param page - Page number for pagination
        @param limit - Number of items per page
        @returns Dictionary with datasets list and pagination info
        """
        logger.info(f"Fetching datasets (page {page}, limit {limit})")
        return self._make_request(
            'GET',
            '/v1/datasets',
            params={'page': page, 'limit': limit}
        )

    def get_all_datasets(self) -> List[Dict]:
        """
        Get all datasets across all pages

        @returns List of all dataset objects
        """
        all_datasets = []
        page = 1
        limit = 20

        while True:
            response = self.list_datasets(page=page, limit=limit)
            datasets = response.get('data', [])
            all_datasets.extend(datasets)

            if not response.get('has_more', False):
                break
            page += 1

        logger.info(f"Retrieved {len(all_datasets)} datasets in total")
        return all_datasets

    def create_dataset(self, name: str, description: str = "") -> Dict:
        """
        Create new knowledge base

        @param name - Name of the dataset
        @param description - Description of the dataset
        @returns Created dataset object
        """
        logger.info(f"Creating dataset: {name}")
        data = {
            'name': name,
            'permission': 'only_me'
        }
        if description:
            data['description'] = description

        return self._make_request('POST', '/v1/datasets', data=data)

    def list_documents(self, dataset_id: str, page: int = 1, limit: int = 20) -> Dict:
        """
        List documents in a dataset

        @param dataset_id - ID of the dataset
        @param page - Page number for pagination
        @param limit - Number of items per page
        @returns Dictionary with documents list and pagination info
        """
        logger.info(f"Fetching documents for dataset {dataset_id} (page {page})")
        return self._make_request(
            'GET',
            f'/v1/datasets/{dataset_id}/documents',
            params={'page': page, 'limit': limit}
        )

    def get_all_documents(self, dataset_id: str) -> List[Dict]:
        """
        Get all documents for a dataset

        @param dataset_id - ID of the dataset
        @returns List of all document objects
        """
        all_documents = []
        page = 1

        while True:
            response = self.list_documents(dataset_id, page=page)
            documents = response.get('data', [])
            all_documents.extend(documents)

            if not response.get('has_more', False):
                break
            page += 1

        logger.info(f"Retrieved {len(all_documents)} documents for dataset {dataset_id}")
        return all_documents

    def get_document_segments(self, dataset_id: str, document_id: str) -> List[Dict]:
        """
        Get all segments/chunks for a document

        @param dataset_id - ID of the dataset
        @param document_id - ID of the document
        @returns List of segment objects
        """
        logger.info(f"Fetching segments for document {document_id}")
        response = self._make_request(
            'GET',
            f'/v1/datasets/{dataset_id}/documents/{document_id}/segments'
        )
        return response.get('data', [])

    def create_document_by_text(
        self,
        dataset_id: str,
        name: str,
        text: str,
        indexing_technique: str = 'high_quality',
        process_rule: Optional[Dict] = None
    ) -> Dict:
        """
        Create document from text

        @param dataset_id - ID of the dataset
        @param name - Name of the document
        @param text - Text content of the document
        @param indexing_technique - Indexing method (high_quality or economy)
        @param process_rule - Processing rules for chunking
        @returns Created document object
        """
        logger.info(f"Creating document by text: {name} in dataset {dataset_id}")

        data = {
            'name': name,
            'text': text,
            'indexing_technique': indexing_technique,
            'process_rule': process_rule or {
                'mode': 'automatic',
                'rules': {}
            }
        }

        return self._make_request(
            'POST',
            f'/v1/datasets/{dataset_id}/document/create_by_text',
            data=data
        )

    def add_segments(
        self,
        dataset_id: str,
        document_id: str,
        segments: List[Dict]
    ) -> Dict:
        """
        Add segments/chunks to a document

        @param dataset_id - ID of the dataset
        @param document_id - ID of the document
        @param segments - List of segment objects with 'content' and optional 'keywords'
        @returns API response
        """
        logger.info(f"Adding {len(segments)} segments to document {document_id}")

        data = {'segments': segments}

        return self._make_request(
            'POST',
            f'/v1/datasets/{dataset_id}/documents/{document_id}/segments',
            data=data
        )

    def delete_dataset(self, dataset_id: str) -> None:
        """
        Delete a dataset

        @param dataset_id - ID of the dataset to delete
        """
        logger.info(f"Deleting dataset {dataset_id}")
        self._make_request('DELETE', f'/v1/datasets/{dataset_id}')


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
        new_document = self.target_client.create_document_by_text(
            dataset_id=dataset_id,
            name=document_name,
            text=combined_text
        )

        # Wait for indexing to complete (increased to 3 seconds for server processing)
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


def load_config_from_env() -> tuple[List[DifyConfig], DifyConfig]:
    """
    Load configuration from .env file
    Supports multiple source API keys separated by comma

    @returns Tuple of (list_of_source_configs, target_config)
    @throws ValueError - If required environment variables are missing
    """
    load_dotenv()

    source_base_url = os.getenv('SOURCE_BASE_URL')
    source_api_keys_raw = os.getenv('SOURCE_API_KEYS')  # Support multiple keys
    target_base_url = os.getenv('TARGET_BASE_URL')
    target_api_key = os.getenv('TARGET_API_KEY')

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
            api_key=api_key
        ))

    target_config = DifyConfig(
        base_url=target_base_url,
        api_key=target_api_key
    )

    logger.info(f"Loaded configuration: {len(source_configs)} source(s), 1 target")
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
