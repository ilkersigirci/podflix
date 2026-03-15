"""Tests for Chainlit auth provider registration."""

from __future__ import annotations

from typing import Any

import chainlit as cl
import pytest

from podflix.env_settings import GENERIC_OAUTH_REQUIRED_ENV_VARS
from podflix.utils.chainlit_utils import auth_provider


def _clear_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var in GENERIC_OAUTH_REQUIRED_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    monkeypatch.delenv("OAUTH_GENERIC_NAME", raising=False)
    monkeypatch.delenv("OAUTH_GENERIC_USER_IDENTIFIER", raising=False)


def _set_required_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    env_values = {
        "OAUTH_GENERIC_CLIENT_ID": "client-id",
        "OAUTH_GENERIC_CLIENT_SECRET": "client-secret",
        "OAUTH_GENERIC_AUTH_URL": "https://example.com/oauth/authorize",
        "OAUTH_GENERIC_TOKEN_URL": "https://example.com/oauth/token",
        "OAUTH_GENERIC_USER_INFO_URL": "https://example.com/oauth/userinfo",
        "OAUTH_GENERIC_SCOPES": "openid profile email",
    }
    for key, value in env_values.items():
        monkeypatch.setenv(key, value)


def _capture_registration_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    captured_callbacks: dict[str, Any] = {}

    def password_decorator(func):
        captured_callbacks["password"] = func
        return func

    def oauth_decorator(func):
        captured_callbacks["oauth"] = func
        return func

    monkeypatch.setattr(auth_provider.cl, "password_auth_callback", password_decorator)
    monkeypatch.setattr(auth_provider.cl, "oauth_callback", oauth_decorator)

    return captured_callbacks


def test_password_auth_type_registers_password_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`AUTH_TYPE=password` should register password auth and delegate auth logic."""
    monkeypatch.setenv("AUTH_TYPE", "password")
    _clear_oauth_env(monkeypatch)
    captured_callbacks = _capture_registration_callbacks(monkeypatch)

    expected_user = cl.User(
        identifier="admin",
        metadata={"role": "admin", "provider": "credentials"},
    )
    called_with: dict[str, tuple[str, str]] = {}

    def fake_simple_auth_callback(username: str, password: str) -> cl.User:
        called_with["credentials"] = (username, password)
        return expected_user

    monkeypatch.setattr(
        auth_provider,
        "simple_auth_callback",
        fake_simple_auth_callback,
    )

    auth_provider.register_auth_provider()

    password_callback = captured_callbacks["password"]
    callback_user = password_callback("alice", "secret")

    assert callback_user is expected_user
    assert called_with["credentials"] == ("alice", "secret")
    assert "oauth" not in captured_callbacks


def test_oauth_auth_type_registers_oauth_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`AUTH_TYPE=oauth` should register oauth callback with Generic provider usage."""
    monkeypatch.setenv("AUTH_TYPE", "oauth")
    _set_required_oauth_env(monkeypatch)
    monkeypatch.setenv("OAUTH_GENERIC_NAME", "my-generic-id")
    captured_callbacks = _capture_registration_callbacks(monkeypatch)

    provider_init_counter = {"count": 0}

    class FakeGenericOAuthProvider:
        id = "generic"

        def __init__(self):
            provider_init_counter["count"] += 1

    monkeypatch.setattr(auth_provider, "GenericOAuthProvider", FakeGenericOAuthProvider)

    auth_provider.register_auth_provider()

    assert provider_init_counter["count"] == 1
    assert "oauth" in captured_callbacks
    assert "password" not in captured_callbacks


@pytest.mark.parametrize(
    ("groups_claim", "expected_role"),
    [
        ("guest", "guest"),
        (["guest", "dev"], "dev"),
        (["admin", "dev"], "admin"),
    ],
)
def test_oauth_role_resolution_from_groups(
    monkeypatch: pytest.MonkeyPatch,
    groups_claim: str | list[str] | None,
    expected_role: str,
) -> None:
    """OAuth callback should derive role from groups with correct priority."""
    monkeypatch.setenv("AUTH_TYPE", "oauth")
    _set_required_oauth_env(monkeypatch)
    monkeypatch.setenv("OAUTH_GENERIC_NAME", "generic-provider")
    captured_callbacks = _capture_registration_callbacks(monkeypatch)

    auth_provider.register_auth_provider()

    oauth_callback = captured_callbacks["oauth"]
    default_app_user = cl.User(
        identifier="user@example.com",
        display_name="Example User",
        metadata={"existing": "value", "provider": "upstream"},
    )

    user = oauth_callback(
        provider_id="generic-provider",
        token="token",
        raw_user_data={"groups": groups_claim},
        default_app_user=default_app_user,
    )

    assert user.identifier == default_app_user.identifier
    assert user.display_name == default_app_user.display_name
    assert user.metadata["existing"] == "value"
    assert expected_role in user.metadata["groups"]
    assert user.metadata["role"] == expected_role
    assert user.metadata["provider"] == "generic-provider"


def test_oauth_user_without_allowed_group_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAuth callback should reject users not in allowed AUTH_GROUPS."""
    monkeypatch.setenv("AUTH_TYPE", "oauth")
    _set_required_oauth_env(monkeypatch)
    monkeypatch.setenv("OAUTH_GENERIC_NAME", "generic-provider")
    captured_callbacks = _capture_registration_callbacks(monkeypatch)

    auth_provider.register_auth_provider()

    oauth_callback = captured_callbacks["oauth"]
    default_app_user = cl.User(identifier="user@example.com", metadata={})

    with pytest.raises(ValueError, match="allowed AUTH_GROUPS"):
        oauth_callback(
            provider_id="generic-provider",
            token="token",
            raw_user_data={"groups": ["family"]},
            default_app_user=default_app_user,
        )


def test_oauth_respects_auth_groups_subset(monkeypatch: pytest.MonkeyPatch) -> None:
    """OAuth callback should use AUTH_GROUPS as allowed group whitelist."""
    monkeypatch.setenv("AUTH_TYPE", "oauth")
    monkeypatch.setenv("AUTH_GROUPS", "dev,guest")
    _set_required_oauth_env(monkeypatch)
    monkeypatch.setenv("OAUTH_GENERIC_NAME", "generic-provider")
    captured_callbacks = _capture_registration_callbacks(monkeypatch)

    auth_provider.register_auth_provider()

    oauth_callback = captured_callbacks["oauth"]
    default_app_user = cl.User(identifier="user@example.com", metadata={})

    with pytest.raises(ValueError, match="allowed AUTH_GROUPS"):
        oauth_callback(
            provider_id="generic-provider",
            token="token",
            raw_user_data={"groups": ["admin"]},
            default_app_user=default_app_user,
        )


def test_oauth_callback_rejects_unconfigured_provider_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAuth callback should only accept the configured generic provider id."""
    monkeypatch.setenv("AUTH_TYPE", "oauth")
    _set_required_oauth_env(monkeypatch)
    monkeypatch.setenv("OAUTH_GENERIC_NAME", "configured-provider")
    captured_callbacks = _capture_registration_callbacks(monkeypatch)

    auth_provider.register_auth_provider()

    oauth_callback = captured_callbacks["oauth"]
    default_app_user = cl.User(identifier="user@example.com", metadata={})

    with pytest.raises(ValueError, match="Expected 'configured-provider'"):
        oauth_callback(
            provider_id="other-provider",
            token="token",
            raw_user_data={"groups": ["dev"]},
            default_app_user=default_app_user,
        )


def test_invalid_auth_type_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid AUTH_TYPE should fail fast with a descriptive error."""
    monkeypatch.setenv("AUTH_TYPE", "saml")
    captured_callbacks = _capture_registration_callbacks(monkeypatch)

    with pytest.raises(ValueError, match="auth_type"):
        auth_provider.register_auth_provider()

    assert "password" not in captured_callbacks
    assert "oauth" not in captured_callbacks


def test_oauth_missing_required_env_vars_raise_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OAuth mode should fail fast when required Generic OAuth vars are missing."""
    monkeypatch.setenv("AUTH_TYPE", "oauth")
    _clear_oauth_env(monkeypatch)
    monkeypatch.setenv("OAUTH_GENERIC_CLIENT_ID", "client-id")
    captured_callbacks = _capture_registration_callbacks(monkeypatch)

    with pytest.raises(ValueError, match="Missing:"):
        auth_provider.register_auth_provider()

    assert "password" not in captured_callbacks
    assert "oauth" not in captured_callbacks
