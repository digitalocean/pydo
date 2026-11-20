# ------------------------------------
# Copyright (c) DigitalOcean.
# Licensed under the Apache-2.0 License.
# ------------------------------------
"""Token and endpoint resolution shared by the sync and async Sandbox SDK."""

import os
from typing import Optional, Tuple

from .errors import AuthenticationError

DEFAULT_API_URL = "https://api.digitalocean.com"


def resolve(token: Optional[str], api_url: Optional[str]) -> Tuple[str, str]:
    """Returns ``(token, api_url)``.

    The token defaults to ``DIGITALOCEAN_ACCESS_TOKEN``; the API origin to
    ``DIGITALOCEAN_API_URL``, then https://api.digitalocean.com.
    """
    resolved = (token or os.environ.get("DIGITALOCEAN_ACCESS_TOKEN") or "").strip()
    if not resolved:
        raise AuthenticationError(
            "no API token: pass `token`, or set DIGITALOCEAN_ACCESS_TOKEN"
        )
    url = api_url or os.environ.get("DIGITALOCEAN_API_URL") or DEFAULT_API_URL
    return resolved, url.rstrip("/")
