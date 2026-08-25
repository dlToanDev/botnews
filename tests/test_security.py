"""Unit test cho security: bcrypt + JWT session token."""
from app.core.security import (
    create_session_token,
    decode_session_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("matkhau123")
    assert h != "matkhau123"
    assert verify_password("matkhau123", h) is True
    assert verify_password("sai", h) is False


def test_session_token_roundtrip():
    token = create_session_token("admin")
    assert decode_session_token(token) == "admin"


def test_invalid_token_returns_none():
    assert decode_session_token("khong-phai-jwt") is None
