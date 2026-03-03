"""
Configuration Manager with Encryption

Handles secure storage and retrieval of sensitive configuration:
- LLM API settings (Base URL, API Key)
- Neo4j connection settings (URI, Username, Password)

Uses Fernet symmetric encryption for sensitive fields.
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class ConfigEncryptionError(Exception):
    """Configuration encryption/decryption error"""
    pass


class ConfigManager:
    """
    Secure configuration manager with encryption support.

    Stores sensitive configuration in encrypted format:
    - LLM API Key
    - Neo4j Password

    Non-sensitive configuration stored in plain text:
    - LLM Base URL
    - Neo4j URI
    - Neo4j Username
    - Other settings
    """

    # Configuration file path
    CONFIG_DIR = Path(__file__).resolve().parent.parent / 'config'
    CONFIG_FILE = CONFIG_DIR / 'user_config.json'
    KEY_FILE = CONFIG_DIR / '.encryption_key'

    # Default configuration
    DEFAULT_CONFIG = {
        'llm': {
            'base_url': 'https://api.deepseek.com',
            'api_key': '',  # Will be encrypted
            'model': 'deepseek-chat',
            'backend': 'openai'
        },
        'neo4j': {
            'uri': 'bolt://localhost:7687',
            'username': 'neo4j',
            'password': '',  # Will be encrypted
            'database': 'neo4j'
        },
        'spacy': {
            'model': 'zh_core_web_sm',
            'confidence_threshold': 0.7
        },
        'visualization': {
            'max_nodes': 500,
            'max_links': 1000,
            'theme': 'light'
        }
    }

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Optional custom config file path
        """
        self.config_file = config_file or self.CONFIG_FILE
        self.key_file = self.KEY_FILE
        self._cipher: Optional[Fernet] = None
        self._config: Dict[str, Any] = {}

        # Ensure config directory exists
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Load or create configuration
        self._load_or_create_config()

    def _get_encryption_key(self) -> bytes:
        """
        Get or create encryption key.

        Key is derived from a master password using PBKDF2HMAC,
        or generated fresh if first time.

        Returns:
            Fernet encryption key (base64 encoded)
        """
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'rb') as f:
                return f.read().strip()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions (Unix-like systems)
            try:
                os.chmod(self.key_file, 0o600)
            except OSError:
                pass  # Windows doesn't support Unix permissions
            logger.info(f"Generated new encryption key: {self.key_file}")
            return key

    @property
    def cipher(self) -> Fernet:
        """Get Fernet cipher instance (lazy initialization)"""
        if self._cipher is None:
            key = self._get_encryption_key()
            self._cipher = Fernet(key)
        return self._cipher

    def _encrypt_value(self, value: str) -> str:
        """
        Encrypt a string value.

        Args:
            value: Plain text value to encrypt

        Returns:
            Base64 encoded encrypted value

        Raises:
            ConfigEncryptionError: If encryption fails
        """
        if not value:
            return ''
        try:
            encrypted = self.cipher.encrypt(value.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ConfigEncryptionError(f"Failed to encrypt value: {e}")

    def _decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt an encrypted value.

        Args:
            encrypted_value: Base64 encoded encrypted value

        Returns:
            Decrypted plain text value

        Raises:
            ConfigEncryptionError: If decryption fails
        """
        if not encrypted_value:
            return ''
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode('utf-8'))
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ConfigEncryptionError(f"Failed to decrypt value: {e}")

    def _load_or_create_config(self) -> None:
        """Load existing config or create with defaults"""
        if self.config_file.exists():
            self._config = self._load_config()
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self._save_config()
            logger.info(f"Created default configuration: {self.config_file}")

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Configuration dictionary
        """
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Merge with defaults for any missing fields
            config = self._deep_merge(self.DEFAULT_CONFIG, data)
            logger.info(f"Loaded configuration from: {self.config_file}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            # Return defaults on parse error
            return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved configuration to: {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_config(self) -> Dict[str, Any]:
        """
        Get full configuration with decrypted sensitive fields.

        Returns:
            Complete configuration dictionary
        """
        config = self._deep_merge(self.DEFAULT_CONFIG, self._config)

        # Decrypt sensitive fields
        if config.get('llm', {}).get('api_key'):
            config['llm']['api_key'] = self._decrypt_value(config['llm']['api_key'])

        if config.get('neo4j', {}).get('password'):
            config['neo4j']['password'] = self._decrypt_value(config['neo4j']['password'])

        return config

    def get_llm_config(self) -> Dict[str, str]:
        """
        Get LLM configuration.

        Returns:
            LLM settings dictionary
        """
        config = self.get_config()
        return config.get('llm', self.DEFAULT_CONFIG['llm'])

    def get_neo4j_config(self) -> Dict[str, str]:
        """
        Get Neo4j configuration.

        Returns:
            Neo4j settings dictionary
        """
        config = self.get_config()
        return config.get('neo4j', self.DEFAULT_CONFIG['neo4j'])

    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.

        Sensitive fields (api_key, password) are automatically encrypted.

        Args:
            updates: Dictionary with configuration updates
        """
        # Encrypt sensitive fields before saving
        if 'llm' in updates and 'api_key' in updates['llm']:
            updates['llm']['api_key'] = self._encrypt_value(updates['llm']['api_key'])

        if 'neo4j' in updates and 'password' in updates['neo4j']:
            updates['neo4j']['password'] = self._encrypt_value(updates['neo4j']['password'])

        # Deep merge updates into current config
        self._config = self._deep_merge(self._config, updates)
        self._save_config()

    def update_llm_config(self, base_url: str = None, api_key: str = None,
                         model: str = None, backend: str = None) -> None:
        """
        Update LLM configuration.

        Args:
            base_url: API base URL
            api_key: API key (will be encrypted)
            model: Model name
            backend: Backend type (openai/ollama/anthropic)
        """
        updates = {'llm': {}}
        if base_url is not None:
            updates['llm']['base_url'] = base_url
        if api_key is not None:
            updates['llm']['api_key'] = api_key
        if model is not None:
            updates['llm']['model'] = model
        if backend is not None:
            updates['llm']['backend'] = backend

        self.update_config(updates)

    def update_neo4j_config(self, uri: str = None, username: str = None,
                           password: str = None, database: str = None) -> None:
        """
        Update Neo4j configuration.

        Args:
            uri: Connection URI
            username: Username
            password: Password (will be encrypted)
            database: Database name
        """
        updates = {'neo4j': {}}
        if uri is not None:
            updates['neo4j']['uri'] = uri
        if username is not None:
            updates['neo4j']['username'] = username
        if password is not None:
            updates['neo4j']['password'] = password
        if database is not None:
            updates['neo4j']['database'] = database

        self.update_config(updates)

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary (safe for logging/display).

        Sensitive fields are masked.

        Returns:
            Configuration summary with masked sensitive fields
        """
        config = self.get_config()

        # Mask sensitive fields
        summary = {
            'llm': {
                'base_url': config.get('llm', {}).get('base_url', ''),
                'api_key': self._mask_value(config.get('llm', {}).get('api_key', '')),
                'model': config.get('llm', {}).get('model', ''),
                'backend': config.get('llm', {}).get('backend', '')
            },
            'neo4j': {
                'uri': config.get('neo4j', {}).get('uri', ''),
                'username': config.get('neo4j', {}).get('username', ''),
                'password': self._mask_value(config.get('neo4j', {}).get('password', '')),
                'database': config.get('neo4j', {}).get('database', '')
            }
        }

        return summary

    def _mask_value(self, value: str, visible_chars: int = 4) -> str:
        """Mask sensitive value for display"""
        if not value:
            return '(not set)'
        if len(value) <= visible_chars:
            return '****'
        return value[:visible_chars] + '****'

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._config = self.DEFAULT_CONFIG.copy()
        self._save_config()
        logger.info("Configuration reset to defaults")

    def validate_config(self) -> Dict[str, bool]:
        """
        Validate current configuration.

        Returns:
            Dictionary with validation results
        """
        config = self.get_config()

        results = {
            'llm_configured': bool(config.get('llm', {}).get('api_key')),
            'neo4j_configured': bool(config.get('neo4j', {}).get('password')),
            'llm_base_url_valid': bool(config.get('llm', {}).get('base_url')),
            'neo4j_uri_valid': bool(config.get('neo4j', {}).get('uri')),
        }

        results['fully_configured'] = all(results.values())

        return results


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config_manager() -> ConfigManager:
    """Reload config manager (for testing)"""
    global _config_manager
    _config_manager = ConfigManager()
    return _config_manager
