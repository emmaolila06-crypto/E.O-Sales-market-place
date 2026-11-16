from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_verifies_and_is_not_plaintext():
    password = "A-long-test-password-123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_contains_user_identity_and_role():
    payload = decode_access_token(create_access_token(42, "seller"))
    assert payload["sub"] == "42"
    assert payload["role"] == "seller"
