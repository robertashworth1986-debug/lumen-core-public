from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping
import re


ENV_REFERENCE = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")

AUTH_ENV_BY_SOURCE = {
    ("youtube", "api_key"): "LUMASCOUT_YOUTUBE_API_KEY",
    ("spotify", "client_id"): "LUMASCOUT_SPOTIFY_CLIENT_ID",
    ("spotify", "client_secret"): "LUMASCOUT_SPOTIFY_CLIENT_SECRET",
    ("meta", "access_token"): "LUMASCOUT_META_ACCESS_TOKEN",
    ("twitter_x", "bearer_token"): "LUMASCOUT_X_BEARER_TOKEN",
    ("ticketmaster", "api_key"): "LUMASCOUT_TICKETMASTER_API_KEY",
    ("news_api", "api_key"): "LUMASCOUT_NEWS_API_KEY",
}


class RegistryCredentialError(ValueError):
    """Raised when tracked registry credentials are not environment references."""


def validate_registry_auth_references(registry: Mapping[str, Any]) -> None:
    sources = registry.get("sources")
    if not isinstance(sources, list):
        raise RegistryCredentialError("registry sources must be a list")

    for source in sources:
        if not isinstance(source, Mapping):
            raise RegistryCredentialError("registry source must be an object")
        source_name = source.get("name")
        if not isinstance(source_name, str) or not source_name:
            raise RegistryCredentialError("registry source name is required")
        auth = source.get("auth", {})
        if not isinstance(auth, Mapping):
            raise RegistryCredentialError(f"{source_name} auth must be an object")

        for key, value in auth.items():
            expected_env = AUTH_ENV_BY_SOURCE.get((source_name, str(key)))
            if expected_env is None:
                raise RegistryCredentialError(
                    f"unregistered auth field: {source_name}.{key}"
                )
            if not isinstance(value, str):
                raise RegistryCredentialError(
                    f"auth reference must be text: {source_name}.{key}"
                )
            match = ENV_REFERENCE.fullmatch(value)
            if match is None or match.group(1) != expected_env:
                raise RegistryCredentialError(
                    f"invalid auth reference: {source_name}.{key}"
                )


def resolve_registry_environment(
    registry: Mapping[str, Any],
    environ: Mapping[str, str],
) -> dict[str, Any]:
    validate_registry_auth_references(registry)
    resolved = deepcopy(dict(registry))
    for source in resolved["sources"]:
        source_name = source["name"]
        for key in source.get("auth", {}):
            env_name = AUTH_ENV_BY_SOURCE[(source_name, key)]
            source["auth"][key] = environ.get(env_name, "")
    return resolved
