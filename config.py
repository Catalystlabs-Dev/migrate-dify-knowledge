"""
Dify Migration Tool - Configuration and Validation

Configuration dataclasses and validation functions for Dify instances.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


def validate_url(url: str) -> str:
    """
    Validate and normalize URL

    @param url - URL to validate
    @returns Normalized URL without trailing slash
    @throws ValueError - If URL is invalid

    @example
    validate_url("https://api.dify.ai/")  # Returns "https://api.dify.ai"
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    url = url.strip()

    if not url.startswith(('http://', 'https://')):
        raise ValueError(f"Invalid URL scheme. Must start with http:// or https://. Got: {url}")

    # Remove trailing slashes for consistency
    return url.rstrip('/')


def validate_api_key(api_key: str, key_type: str = "API key") -> str:
    """
    Validate API key format

    @param api_key - API key to validate
    @param key_type - Type description for error messages
    @returns Validated and trimmed API key
    @throws ValueError - If API key is invalid

    @example
    validate_api_key("dataset-abc123", "Dataset API key")
    """
    if not api_key or not isinstance(api_key, str):
        raise ValueError(f"{key_type} must be a non-empty string")

    api_key = api_key.strip()

    if len(api_key) < 10:
        raise ValueError(f"{key_type} appears to be too short (minimum 10 characters)")

    return api_key


def validate_email(email: str) -> bool:
    """
    Basic email validation

    @param email - Email address to validate
    @returns True if valid email format

    @example
    validate_email("user@example.com")  # Returns True
    """
    if not email or not isinstance(email, str):
        return False

    email = email.strip()

    # Basic checks
    if '@' not in email:
        return False

    if email.count('@') != 1:
        return False

    local, domain = email.split('@')

    if not local or not domain:
        return False

    if '.' not in domain:
        return False

    return True


def validate_credentials(email: Optional[str], password: Optional[str]) -> Tuple[bool, str]:
    """
    Validate Console API credentials

    @param email - User email
    @param password - User password
    @returns Tuple of (is_valid, error_message)

    @example
    is_valid, error = validate_credentials("user@example.com", "password123")
    if not is_valid:
        print(f"Error: {error}")
    """
    # Both empty is valid (workflow migration disabled)
    if not email and not password:
        return True, ""

    # Must have both or neither
    if email and not password:
        return False, "Password required when email is provided"

    if password and not email:
        return False, "Email required when password is provided"

    # Validate email format
    if email and not validate_email(email):
        return False, f"Invalid email format: {email}"

    # Validate password strength
    if password and len(password) < 6:
        return False, "Password must be at least 6 characters long"

    return True, ""


@dataclass
class DifyConfig:
    """
    Configuration for a Dify instance

    This class holds all necessary configuration for connecting to a Dify instance,
    including both Knowledge Base API and Console API credentials.

    @param base_url - Base URL of Dify instance (e.g., https://api.dify.ai)
    @param api_key - Knowledge Base API key (starts with 'dataset-')
    @param email - Optional email for Console API login (required for workflow migration)
    @param password - Optional password for Console API login (required for workflow migration)

    @example
    # Knowledge Base only
    config = DifyConfig(
        base_url="https://api.dify.ai",
        api_key="dataset-abc123"
    )

    # With workflow migration support
    config = DifyConfig(
        base_url="https://api.dify.ai",
        api_key="dataset-abc123",
        email="user@example.com",
        password="secure_password"
    )
    """
    base_url: str
    api_key: str
    email: Optional[str] = None
    password: Optional[str] = None

    def __post_init__(self) -> None:
        """
        Validate and normalize configuration after initialization

        @throws ValueError - If any configuration value is invalid
        """
        # Validate and normalize URL
        self.base_url = validate_url(self.base_url)

        # Validate API key
        self.api_key = validate_api_key(self.api_key, "Dataset API key")

        # Validate credentials if provided
        is_valid, error_message = validate_credentials(self.email, self.password)
        if not is_valid:
            raise ValueError(f"Invalid credentials: {error_message}")

    @property
    def has_console_credentials(self) -> bool:
        """
        Check if Console API credentials are available

        @returns True if both email and password are configured

        @example
        if config.has_console_credentials:
            # Can use workflow migration features
            pass
        """
        return bool(self.email and self.password)

    @property
    def console_base_url(self) -> str:
        """
        Get base URL for Console API (without /v1 suffix)

        Console API endpoints don't use the /v1 prefix that the Knowledge Base API uses.

        @returns Base URL suitable for Console API calls

        @example
        # If base_url is "https://api.dify.ai/v1"
        config.console_base_url  # Returns "https://api.dify.ai"
        """
        return self.base_url.replace('/v1', '')

    def __repr__(self) -> str:
        """
        String representation of configuration (hides sensitive data)

        @returns Safe string representation
        """
        masked_key = f"{self.api_key[:10]}...{self.api_key[-4:]}" if len(self.api_key) > 14 else "***"
        return (
            f"DifyConfig("
            f"base_url='{self.base_url}', "
            f"api_key='{masked_key}', "
            f"has_console_creds={self.has_console_credentials})"
        )
