"""
API Key Management Model
Provides persistent storage for API keys with hashing and expiration
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from app.models import db


class ApiKey(db.Model):
    """
    API Key model for service account authentication.

    Attributes:
        id: Primary key
        key_hash: Hashed API key (bcrypt)
        key_prefix: First 8 characters of the key for identification
        name: Descriptive name for the API key
        user_id: Associated user ID
        is_active: Whether the key is active
        expires_at: Expiration datetime (None for no expiration)
        last_used_at: Last time the key was used
        created_at: Creation timestamp
        updated_at: Update timestamp
    """

    __tablename__ = "api_keys"

    id = db.Column(db.Integer, primary_key=True)
    key_hash = db.Column(db.String(255), nullable=False, unique=True)
    key_prefix = db.Column(db.String(16), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", backref=db.backref("api_keys", lazy="dynamic"))

    def __repr__(self):
        return f"<ApiKey {self.key_prefix}... ({self.name})>"

    @staticmethod
    def generate_key() -> str:
        """
        Generate a secure random API key.

        Returns:
            str: API key in format 'bms_' + 48 random characters
        """
        # Generate 36 bytes = 48 characters in base64
        random_part = secrets.token_urlsafe(36)
        # Add prefix for easy identification
        return f"bms_{random_part}"

    @staticmethod
    def create_api_key(user_id: int, name: str, expires_in_days: Optional[int] = None) -> tuple[str, "ApiKey"]:
        """
        Create a new API key for a user.

        Args:
            user_id: User ID to associate with the key
            name: Descriptive name for the key
            expires_in_days: Days until expiration (None for no expiration)

        Returns:
            Tuple of (plaintext_key, ApiKey_object)
        """
        # Generate the key
        plaintext_key = ApiKey.generate_key()

        # Extract prefix for identification
        key_prefix = plaintext_key[:12]  # "bms_" + first 8 chars

        # Hash the key for storage
        key_hash = generate_password_hash(plaintext_key, method="pbkdf2:sha256")

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create database record
        api_key = ApiKey(key_hash=key_hash, key_prefix=key_prefix, name=name, user_id=user_id, expires_at=expires_at)

        db.session.add(api_key)
        db.session.commit()

        # Return both plaintext (for user to save) and object
        return plaintext_key, api_key

    @staticmethod
    def verify_key(plaintext_key: str) -> Optional["ApiKey"]:
        """
        Verify an API key and return the associated ApiKey object.

        Args:
            plaintext_key: The plaintext API key to verify

        Returns:
            ApiKey object if valid, None otherwise
        """
        # Extract prefix
        if not plaintext_key.startswith("bms_") or len(plaintext_key) < 12:
            return None

        key_prefix = plaintext_key[:12]

        # Find candidate keys with matching prefix
        candidates = ApiKey.query.filter_by(key_prefix=key_prefix, is_active=True).all()

        for api_key in candidates:
            # Check if expired
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                continue

            # Verify hash
            if check_password_hash(api_key.key_hash, plaintext_key):
                # Update last used timestamp
                api_key.last_used_at = datetime.utcnow()
                db.session.commit()
                return api_key

        return None

    def revoke(self):
        """Revoke (deactivate) this API key."""
        self.is_active = False
        db.session.commit()

    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.utcnow()

    def to_dict(self, include_key: bool = False) -> dict:
        """
        Convert to dictionary representation.

        Args:
            include_key: Whether to include the key_prefix (default: False)

        Returns:
            Dictionary representation
        """
        data = {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat(),
            "is_expired": self.is_expired(),
        }

        if include_key:
            data["key_prefix"] = self.key_prefix + "..."

        return data


class RefreshToken(db.Model):
    """
    Refresh Token model for JWT token renewal.

    Attributes:
        id: Primary key
        token_hash: Hashed refresh token
        user_id: Associated user ID
        expires_at: Expiration datetime
        is_revoked: Whether the token has been revoked
        created_at: Creation timestamp
    """

    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(255), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", backref=db.backref("refresh_tokens", lazy="dynamic"))

    def __repr__(self):
        return f"<RefreshToken user_id={self.user_id}>"

    @staticmethod
    def create_refresh_token(user_id: int, token: str, expires_in_days: int = 30) -> "RefreshToken":
        """
        Create a new refresh token record.

        Args:
            user_id: User ID
            token: JWT refresh token
            expires_in_days: Days until expiration

        Returns:
            RefreshToken object
        """
        # Hash the token
        token_hash = generate_password_hash(token, method="pbkdf2:sha256")

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create record
        refresh_token = RefreshToken(token_hash=token_hash, user_id=user_id, expires_at=expires_at)

        db.session.add(refresh_token)
        db.session.commit()

        return refresh_token

    @staticmethod
    def verify_token(token: str) -> Optional["RefreshToken"]:
        """
        Verify a refresh token.

        Args:
            token: JWT refresh token

        Returns:
            RefreshToken object if valid, None otherwise
        """
        # Find all non-revoked, non-expired tokens
        candidates = RefreshToken.query.filter_by(is_revoked=False).filter(RefreshToken.expires_at > datetime.utcnow()).all()

        for refresh_token in candidates:
            if check_password_hash(refresh_token.token_hash, token):
                return refresh_token

        return None

    def revoke(self):
        """Revoke this refresh token."""
        self.is_revoked = True
        db.session.commit()

    def is_expired(self) -> bool:
        """Check if the refresh token has expired."""
        return self.expires_at < datetime.utcnow()
