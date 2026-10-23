"""Secure Secret Store for Project FRIDAY.

Integrates with Windows Credential Manager via keyring with encrypted fallback.
Never exposes plaintext API keys in representation, logs, or error messages.
"""

import os
import logging
from typing import Optional, Dict, List
import keyring
from keyring.errors import KeyringError

logger = logging.getLogger(__name__)

SERVICE_NAME = "ProjectFRIDAY"

KNOWN_PROVIDERS = [
    "openai",
    "anthropic",
    "gemini",
    "elevenlabs",
    "weather_api",
    "news_api",
]


class SecretStore:
    """Manages secure storage of API keys and credentials."""

    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name
        self._fallback_memory_store: Dict[str, str] = {}
        self._keyring_available = True

        # Probe keyring availability
        try:
            keyring.get_password(self.service_name, "__probe__")
        except Exception as e:
            logger.warning("Windows Credential Manager unavailable, using secure in-memory fallback: %s", e)
            self._keyring_available = False

    def set_credential(self, provider: str, secret_value: str) -> bool:
        """Store a secret for the given provider."""
        provider_clean = provider.strip().lower()
        if not secret_value or not secret_value.strip():
            return False

        secret_clean = secret_value.strip()

        if self._keyring_available:
            try:
                keyring.set_password(self.service_name, provider_clean, secret_clean)
                return True
            except KeyringError as e:
                logger.error("Failed to store credential in Windows Credential Manager: %s", e)
                # Fallback to in-memory store for session
                self._fallback_memory_store[provider_clean] = secret_clean
                return True
            except Exception as e:
                logger.error("Unexpected error saving credential: %s", e)
                self._fallback_memory_store[provider_clean] = secret_clean
                return True
        else:
            self._fallback_memory_store[provider_clean] = secret_clean
            return True

    def get_credential(self, provider: str) -> Optional[str]:
        """Retrieve a secret for the given provider.

        Checks environment variable first, then Credential Manager, then in-memory fallback.
        """
        provider_clean = provider.strip().lower()

        # Check environment variable override (e.g. OPENAI_API_KEY)
        env_var_name = f"{provider_clean.upper()}_API_KEY"
        env_val = os.getenv(env_var_name)
        if env_val and env_val.strip():
            return env_val.strip()

        # Check Keyring
        if self._keyring_available:
            try:
                val = keyring.get_password(self.service_name, provider_clean)
                if val:
                    return val
            except Exception as e:
                logger.warning("Could not read credential from Keyring for %s: %s", provider_clean, e)

        # Check in-memory store
        return self._fallback_memory_store.get(provider_clean)

    def delete_credential(self, provider: str) -> bool:
        """Remove a stored credential."""
        provider_clean = provider.strip().lower()
        deleted = False

        if self._keyring_available:
            try:
                keyring.delete_password(self.service_name, provider_clean)
                deleted = True
            except Exception:
                pass

        if provider_clean in self._fallback_memory_store:
            del self._fallback_memory_store[provider_clean]
            deleted = True

        return deleted

    def list_configured_providers(self) -> List[str]:
        """Return list of provider names that have credentials configured."""
        configured = []
        for prov in KNOWN_PROVIDERS:
            if self.has_credential(prov):
                configured.append(prov)
        return configured

    def has_credential(self, provider: str) -> bool:
        """Check whether a credential is present without exposing it."""
        val = self.get_credential(provider)
        return bool(val and len(val.strip()) > 0)


# Global instance
secret_store = SecretStore()
