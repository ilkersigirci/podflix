"""Shared authentication provider registration for Chainlit apps."""

from __future__ import annotations

from typing import Any

import chainlit as cl
from chainlit.oauth_providers import GenericOAuthProvider

from podflix.env_settings import env_settings

ROLE_PRIORITY = ("admin", "dev", "guest")


def simple_auth_callback(username: str, password: str) -> cl.User:
    """Authenticate user with simple username and password check.

    Examples:
        >>> simple_auth_callback("admin", "admin")
        User(identifier="admin", metadata={"role": "admin", "provider": "credentials"})

    Args:
        username: A string representing the username for authentication.
        password: A string representing the password for authentication.

    Returns:
        A User object if authentication is successful.

    Raises:
        ValueError: If credentials are invalid.
    """
    if (username, password) == (
        env_settings.admin_username,
        env_settings.admin_password,
    ):
        return cl.User(
            identifier=username, metadata={"role": "admin", "provider": "credentials"}
        )

    raise ValueError("Invalid credentials")


def _build_oauth_user(
    default_app_user: cl.User, role: str, groups: list[str], provider_id: str
) -> cl.User:
    """Create the final app user by merging metadata into default_app_user."""
    merged_metadata = {
        **(default_app_user.metadata or {}),
        "role": role,
        "groups": groups,
        "provider": provider_id,
    }
    return cl.User(
        identifier=default_app_user.identifier,
        display_name=default_app_user.display_name,
        metadata=merged_metadata,
    )


def register_auth_provider() -> None:
    """Register Chainlit authentication callback based on AUTH_TYPE."""
    if env_settings.auth_type == "password":

        @cl.password_auth_callback
        def auth_callback(username: str, password: str):
            return simple_auth_callback(username, password)

        return

    generic_provider = GenericOAuthProvider()
    configured_provider_id = (
        env_settings.oauth_generic_name.strip() or generic_provider.id
    )
    allowed_groups = set(env_settings.auth_groups.split(","))

    @cl.oauth_callback
    def oauth_auth_callback(
        provider_id: str,
        token: str,
        raw_user_data: dict[str, Any],
        default_app_user: cl.User,
        id_token: str | None = None,
    ):
        del token, id_token

        if provider_id != configured_provider_id:
            raise ValueError(
                f"Invalid oauth provider {provider_id!r}. "
                f"Expected {configured_provider_id!r}."
            )

        groups_claim = raw_user_data.get("groups")
        if isinstance(groups_claim, str):
            groups = [groups_claim.strip().lower()] if groups_claim.strip() else []
        elif isinstance(groups_claim, list):
            groups = [
                group.strip().lower()
                for group in groups_claim
                if isinstance(group, str) and group.strip()
            ]
        else:
            groups = []

        groups_set = set(groups)
        role = next(
            (
                candidate_role
                for candidate_role in ROLE_PRIORITY
                if candidate_role in groups_set and candidate_role in allowed_groups
            ),
            None,
        )
        if role is None:
            allowed = env_settings.auth_groups
            raise ValueError(
                f"OAuth user is not in allowed AUTH_GROUPS. Allowed values: {allowed}."
            )

        return _build_oauth_user(
            default_app_user=default_app_user,
            role=role,
            groups=groups,
            provider_id=configured_provider_id,
        )
