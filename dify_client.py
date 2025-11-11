"""
Dify API Client

HTTP client for interacting with Dify Knowledge Base API and Console API.
Handles authentication, retries, rate limiting, and error handling.
"""

import requests
import time
from typing import Dict, List, Optional

from constants import APIEndpoints, MigrationDefaults
from config import DifyConfig
from logger_utils import get_logger


logger = get_logger(__name__)


class DifyClient:
    """
    Client for interacting with Dify API

    Provides methods for both Knowledge Base API (datasets, documents, segments)
    and Console API (apps, workflows, DSL export/import).

    @example
    config = DifyConfig(base_url="https://api.dify.ai", api_key="dataset-123")
    client = DifyClient(config)
    datasets = client.get_all_datasets()
    """

    def __init__(self, config: DifyConfig):
        """
        Initialize Dify client

        @param config - DifyConfig object with base_url, api_key, and optional credentials
        """
        self.config = config
        self.headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        }
        self.console_access_token = None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = MigrationDefaults.MAX_RETRIES,
        retry_delay: float = MigrationDefaults.RETRY_DELAY
    ) -> Dict:
        """
        Make HTTP request to Dify API with retry logic

        @param method - HTTP method (GET, POST, DELETE, etc.)
        @param endpoint - API endpoint path
        @param data - Request body data
        @param files - Files to upload
        @param params - Query parameters
        @param max_retries - Maximum retries for 500 errors
        @param retry_delay - Initial delay between retries
        @returns API response as dictionary
        @throws requests.exceptions.RequestException - On failure after retries
        """
        url = f"{self.config.base_url}{endpoint}"
        headers = self.headers.copy()

        if files:
            headers.pop('Content-Type', None)

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
                    timeout=MigrationDefaults.REQUEST_TIMEOUT,
                    verify=True
                )
                response.raise_for_status()
                time.sleep(MigrationDefaults.RATE_LIMIT_DELAY)
                return response.json() if response.content else {}

            except requests.exceptions.SSLError as ssl_error:
                logger.error(f"SSL Certificate error: {str(ssl_error)}")
                logger.warning("Retrying with SSL verification disabled")
                try:
                    response = requests.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data if not files else None,
                        files=files,
                        params=params,
                        timeout=MigrationDefaults.REQUEST_TIMEOUT,
                        verify=False
                    )
                    response.raise_for_status()
                    time.sleep(MigrationDefaults.RATE_LIMIT_DELAY)
                    return response.json() if response.content else {}
                except requests.exceptions.RequestException as retry_error:
                    logger.error(f"Retry failed: {str(retry_error)}")
                    raise

            except requests.exceptions.HTTPError as http_error:
                if hasattr(http_error, 'response') and http_error.response is not None:
                    status_code = http_error.response.status_code

                    if status_code == 500 and attempt < max_retries:
                        wait_time = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"500 Server Error on attempt {attempt + 1}/{max_retries + 1}. "
                            f"Retrying in {wait_time:.1f} seconds..."
                        )
                        time.sleep(wait_time)
                        last_error = http_error
                        continue
                    else:
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

        if last_error:
            logger.error(f"Failed after {max_retries + 1} attempts")
            raise last_error

        raise requests.exceptions.RequestException("Request failed unexpectedly")

    # Knowledge Base API Methods

    def list_datasets(self, page: int = 1, limit: int = MigrationDefaults.PAGE_SIZE) -> Dict:
        """List datasets with pagination"""
        logger.info(f"Fetching datasets (page {page}, limit {limit})")
        return self._make_request('GET', APIEndpoints.DATASETS, params={'page': page, 'limit': limit})

    def get_all_datasets(self) -> List[Dict]:
        """Get all datasets across all pages"""
        all_datasets = []
        page = 1

        while True:
            response = self.list_datasets(page=page)
            datasets = response.get('data', [])
            all_datasets.extend(datasets)

            if not response.get('has_more', False):
                break
            page += 1

        logger.info(f"Retrieved {len(all_datasets)} datasets in total")
        return all_datasets

    def create_dataset(self, name: str, description: str = "") -> Dict:
        """Create new knowledge base"""
        logger.info(f"Creating dataset: {name}")
        data = {'name': name, 'permission': 'only_me'}
        if description:
            data['description'] = description
        return self._make_request('POST', APIEndpoints.DATASETS, data=data)

    def list_documents(self, dataset_id: str, page: int = 1, limit: int = MigrationDefaults.PAGE_SIZE) -> Dict:
        """List documents in a dataset"""
        logger.info(f"Fetching documents for dataset {dataset_id} (page {page})")
        endpoint = APIEndpoints.DOCUMENTS.format(dataset_id=dataset_id)
        return self._make_request('GET', endpoint, params={'page': page, 'limit': limit})

    def get_all_documents(self, dataset_id: str) -> List[Dict]:
        """Get all documents for a dataset"""
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
        """Get all segments/chunks for a document"""
        logger.info(f"Fetching segments for document {document_id}")
        endpoint = APIEndpoints.SEGMENTS.format(dataset_id=dataset_id, document_id=document_id)
        response = self._make_request('GET', endpoint)
        return response.get('data', [])

    def create_document_by_text(
        self,
        dataset_id: str,
        name: str,
        text: str,
        indexing_technique: str = 'high_quality',
        process_rule: Optional[Dict] = None
    ) -> Dict:
        """Create document from text"""
        logger.info(f"Creating document by text: {name} in dataset {dataset_id}")

        data = {
            'name': name,
            'text': text,
            'indexing_technique': indexing_technique,
            'process_rule': process_rule or {'mode': 'automatic', 'rules': {}}
        }

        endpoint = APIEndpoints.CREATE_BY_TEXT.format(dataset_id=dataset_id)
        return self._make_request('POST', endpoint, data=data)

    def add_segments(self, dataset_id: str, document_id: str, segments: List[Dict]) -> Dict:
        """Add segments/chunks to a document"""
        logger.info(f"Adding {len(segments)} segments to document {document_id}")
        endpoint = APIEndpoints.SEGMENTS.format(dataset_id=dataset_id, document_id=document_id)
        return self._make_request('POST', endpoint, data={'segments': segments})

    def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset"""
        logger.info(f"Deleting dataset {dataset_id}")
        endpoint = APIEndpoints.DATASET_DETAIL.format(dataset_id=dataset_id)
        self._make_request('DELETE', endpoint)

    # Console API Methods (Workflows/Apps)

    def console_login(self) -> str:
        """Login to Console API to get access token"""
        if not self.config.has_console_credentials:
            raise ValueError("Email and password required for Console API login")

        logger.info(f"Logging in to Console API with email: {self.config.email}")

        try:
            response = requests.post(
                f"{self.config.console_base_url}{APIEndpoints.CONSOLE_LOGIN}",
                json={'email': self.config.email, 'password': self.config.password},
                headers={'Content-Type': 'application/json'},
                timeout=MigrationDefaults.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            result = response.json()
            access_token = result.get('data', {}).get('access_token')

            if not access_token:
                raise ValueError("No access token in login response")

            self.console_access_token = access_token
            logger.info("Successfully logged in to Console API")
            return access_token

        except requests.exceptions.RequestException as error:
            logger.error(f"Console API login failed: {str(error)}")
            if hasattr(error, 'response') and error.response is not None:
                logger.error(f"Response: {error.response.text}")
            raise

    def _ensure_console_login(self) -> None:
        """Ensure we have a valid console access token"""
        if not self.console_access_token:
            self.console_login()

    def list_apps(self, page: int = 1, limit: int = MigrationDefaults.APPS_PAGE_SIZE) -> Dict:
        """List all apps/workflows using Console API"""
        self._ensure_console_login()

        logger.info(f"Fetching apps (page {page}, limit {limit})")

        headers = {
            'Authorization': f'Bearer {self.console_access_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(
                f"{self.config.console_base_url}{APIEndpoints.CONSOLE_APPS}",
                params={'page': page, 'limit': limit},
                headers=headers,
                timeout=MigrationDefaults.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as error:
            logger.error(f"Failed to list apps: {str(error)}")
            if hasattr(error, 'response') and error.response is not None:
                logger.error(f"Response: {error.response.text}")
            raise

    def get_all_apps(self) -> List[Dict]:
        """Get all apps/workflows across all pages"""
        all_apps = []
        page = 1

        while True:
            response = self.list_apps(page=page)
            apps = response.get('data', [])
            all_apps.extend(apps)

            if not response.get('has_more', False):
                break
            page += 1

        logger.info(f"Retrieved {len(all_apps)} apps in total")
        return all_apps

    def export_app_dsl(self, app_id: str, include_secret: bool = False) -> str:
        """Export app/workflow as DSL (YAML format)"""
        self._ensure_console_login()

        logger.info(f"Exporting app {app_id} DSL (include_secret={include_secret})")

        headers = {'Authorization': f'Bearer {self.console_access_token}'}
        endpoint = APIEndpoints.CONSOLE_APP_EXPORT.format(app_id=app_id)

        try:
            response = requests.get(
                f"{self.config.console_base_url}{endpoint}",
                params={'include_secret': str(include_secret).lower()},
                headers=headers,
                timeout=MigrationDefaults.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            dsl_content = response.text
            logger.info(f"Successfully exported app {app_id} DSL ({len(dsl_content)} bytes)")
            return dsl_content

        except requests.exceptions.RequestException as error:
            logger.error(f"Failed to export app {app_id}: {str(error)}")
            if hasattr(error, 'response') and error.response is not None:
                logger.error(f"Response: {error.response.text}")
            raise

    def import_app_dsl(
        self,
        yaml_content: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon_type: Optional[str] = None,
        icon: Optional[str] = None,
        icon_background: Optional[str] = None
    ) -> Dict:
        """Import app/workflow from DSL (YAML format)"""
        self._ensure_console_login()

        logger.info(f"Importing app from DSL ({len(yaml_content)} bytes)")

        headers = {
            'Authorization': f'Bearer {self.console_access_token}',
            'Content-Type': 'application/json'
        }

        data = {'mode': 'yaml-content', 'yaml_content': yaml_content}

        if name:
            data['name'] = name
        if description:
            data['description'] = description
        if icon_type:
            data['icon_type'] = icon_type
        if icon:
            data['icon'] = icon
        if icon_background:
            data['icon_background'] = icon_background

        try:
            response = requests.post(
                f"{self.config.console_base_url}{APIEndpoints.CONSOLE_APP_IMPORT}",
                json=data,
                headers=headers,
                timeout=MigrationDefaults.IMPORT_TIMEOUT
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Successfully imported app: {result.get('data', {}).get('app', {}).get('name')}")
            return result

        except requests.exceptions.RequestException as error:
            logger.error(f"Failed to import app: {str(error)}")
            if hasattr(error, 'response') and error.response is not None:
                logger.error(f"Response: {error.response.text}")
            raise
