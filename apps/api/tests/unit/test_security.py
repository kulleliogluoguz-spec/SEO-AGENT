"""Unit tests for security utilities."""
import pytest
from jose import JWTError

from app.core.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_subject,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "MySecureP@ss1"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-password-1")
        assert not verify_password("wrong-password-1", hashed)

    def test_different_hashes_for_same_password(self):
        """bcrypt should produce different hashes due to salt."""
        p = "SamePassword1!"
        assert hash_password(p) != hash_password(p)


class TestJWTTokens:
    def test_create_and_decode_access_token(self):
        token = create_access_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        token = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_token("not-a-valid-token")

    def test_get_token_subject(self):
        token = create_access_token("user-789")
        assert get_token_subject(token) == "user-789"

    def test_get_subject_invalid_returns_none(self):
        assert get_token_subject("garbage") is None

    def test_token_with_extra_data(self):
        token = create_access_token("user-001", extra={"role": "admin"})
        payload = decode_token(token)
        assert payload["role"] == "admin"
