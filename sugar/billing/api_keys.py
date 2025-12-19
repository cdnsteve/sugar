"""
API Key Management for Sugar SaaS

Manages customer API keys for authentication:
- Key generation and validation
- Rate limiting
- Scope management
"""

import hashlib
import hmac
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """An API key for a customer"""

    key_id: str  # Public identifier (sk_sugar_...)
    key_hash: str  # SHA-256 hash of the actual key
    customer_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    scopes: List[str] = field(default_factory=list)
    rate_limit: int = 1000  # Requests per hour
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "key_hash": self.key_hash,
            "customer_id": self.customer_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "scopes": self.scopes,
            "rate_limit": self.rate_limit,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APIKey":
        return cls(
            key_id=data["key_id"],
            key_hash=data["key_hash"],
            customer_id=data["customer_id"],
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None,
            scopes=data.get("scopes", []),
            rate_limit=data.get("rate_limit", 1000),
            is_active=data.get("is_active", True),
            metadata=data.get("metadata", {}),
        )

    def is_expired(self) -> bool:
        """Check if the key is expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def has_scope(self, scope: str) -> bool:
        """Check if the key has a specific scope"""
        if "*" in self.scopes:
            return True
        return scope in self.scopes


@dataclass
class RateLimitInfo:
    """Rate limit information for a key"""

    key_id: str
    limit: int
    remaining: int
    reset_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat(),
        }


class APIKeyManager:
    """
    Manage API keys for Sugar SaaS.

    Provides:
    - Key generation with secure random tokens
    - Key validation and authentication
    - Rate limiting per key
    - Scope-based authorization
    """

    KEY_PREFIX = "sk_sugar_"

    def __init__(
        self,
        storage_path: Optional[str] = None,
        signing_secret: Optional[str] = None,
    ):
        """
        Initialize the API key manager.

        Args:
            storage_path: Path to store keys (defaults to .sugar/keys/)
            signing_secret: Secret for key signing (defaults to env var)
        """
        self.storage_path = storage_path or os.path.join(
            os.path.expanduser("~"), ".sugar", "keys"
        )
        self.signing_secret = signing_secret or os.environ.get(
            "SUGAR_SIGNING_SECRET",
            secrets.token_hex(32),  # Generate if not provided
        )

        # In-memory cache for rate limiting
        self._rate_limit_cache: Dict[str, Dict[str, Any]] = {}

        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)

    def generate_key(
        self,
        customer_id: str,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
        rate_limit: int = 1000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[APIKey, str]:
        """
        Generate a new API key.

        Args:
            customer_id: Customer identifier
            name: Key name/description
            scopes: Allowed scopes (defaults to ['*'])
            expires_in_days: Days until expiration (None = never)
            rate_limit: Requests per hour
            metadata: Additional metadata

        Returns:
            Tuple of (APIKey object, actual key string)
        """
        # Generate secure random key
        key_bytes = secrets.token_bytes(32)
        key_string = self.KEY_PREFIX + secrets.token_urlsafe(32)

        # Hash the key for storage
        key_hash = self._hash_key(key_string)

        # Generate key ID
        key_id = self.KEY_PREFIX + secrets.token_hex(8)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            customer_id=customer_id,
            name=name,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            scopes=scopes or ["*"],
            rate_limit=rate_limit,
            metadata=metadata or {},
        )

        # Store the key
        self._save_key(api_key)

        logger.info(f"Generated API key {key_id} for customer {customer_id}")

        return api_key, key_string

    def validate_key(self, key_string: str) -> Optional[APIKey]:
        """
        Validate an API key.

        Args:
            key_string: The full API key string

        Returns:
            APIKey if valid, None if invalid
        """
        if not key_string.startswith(self.KEY_PREFIX):
            return None

        key_hash = self._hash_key(key_string)

        # Search for matching key
        for filename in os.listdir(self.storage_path):
            if not filename.endswith(".json"):
                continue

            key = self._load_key(filename)
            if key and key.key_hash == key_hash:
                # Check if active and not expired
                if not key.is_active:
                    logger.warning(f"Inactive key used: {key.key_id}")
                    return None

                if key.is_expired():
                    logger.warning(f"Expired key used: {key.key_id}")
                    return None

                # Update last used timestamp
                key.last_used_at = datetime.utcnow()
                self._save_key(key)

                return key

        return None

    def check_rate_limit(self, key: APIKey) -> RateLimitInfo:
        """
        Check and update rate limit for a key.

        Args:
            key: The API key to check

        Returns:
            RateLimitInfo with current limits
        """
        now = datetime.utcnow()
        cache_key = key.key_id

        # Get or initialize rate limit info
        if cache_key not in self._rate_limit_cache:
            self._rate_limit_cache[cache_key] = {
                "count": 0,
                "reset_at": now + timedelta(hours=1),
            }

        cache = self._rate_limit_cache[cache_key]

        # Reset if window has passed
        if now > cache["reset_at"]:
            cache["count"] = 0
            cache["reset_at"] = now + timedelta(hours=1)

        # Increment count
        cache["count"] += 1

        remaining = max(0, key.rate_limit - cache["count"])

        return RateLimitInfo(
            key_id=key.key_id,
            limit=key.rate_limit,
            remaining=remaining,
            reset_at=cache["reset_at"],
        )

    def is_rate_limited(self, key: APIKey) -> bool:
        """Check if a key is currently rate limited"""
        info = self.check_rate_limit(key)
        return info.remaining <= 0

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: The key ID to revoke

        Returns:
            True if revoked, False if not found
        """
        filename = f"{key_id}.json"
        key = self._load_key(filename)

        if key:
            key.is_active = False
            self._save_key(key)
            logger.info(f"Revoked API key {key_id}")
            return True

        return False

    def list_keys(
        self,
        customer_id: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[APIKey]:
        """
        List API keys.

        Args:
            customer_id: Filter by customer (optional)
            include_inactive: Include revoked keys

        Returns:
            List of API keys
        """
        keys = []

        for filename in os.listdir(self.storage_path):
            if not filename.endswith(".json"):
                continue

            key = self._load_key(filename)
            if not key:
                continue

            # Apply filters
            if customer_id and key.customer_id != customer_id:
                continue

            if not include_inactive and not key.is_active:
                continue

            keys.append(key)

        return sorted(keys, key=lambda k: k.created_at, reverse=True)

    def _hash_key(self, key_string: str) -> str:
        """Create a secure hash of the key"""
        return hmac.new(
            self.signing_secret.encode(),
            key_string.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _save_key(self, key: APIKey) -> None:
        """Save a key to storage"""
        file_path = os.path.join(self.storage_path, f"{key.key_id}.json")
        with open(file_path, "w") as f:
            json.dump(key.to_dict(), f, indent=2)

    def _load_key(self, filename: str) -> Optional[APIKey]:
        """Load a key from storage"""
        file_path = os.path.join(self.storage_path, filename)
        try:
            with open(file_path) as f:
                return APIKey.from_dict(json.load(f))
        except Exception as e:
            logger.error(f"Error loading key {filename}: {e}")
            return None
