"""Authentication manager handling OAuth2 token generation and caching for Palo Alto Networks APIs."""

import time
import requests
from typing import Optional
from .config import Config


class PANWAuthManager:
    """Manages authentication with Palo Alto Networks Strata / SASE APIs.
    
    Supports:
    1. OAuth2 client_credentials token grant via PANW Identity Services with auto-caching and auto-refresh.
    2. Static Bearer Token support for manual or pre-generated tokens.
    """

    def __init__(self, config: Config):
        self.config = config
        self._cached_token: Optional[str] = None
        self._token_expiry_timestamp: float = 0.0

    def get_access_token(self, force_refresh: bool = False) -> str:
        """Return a valid Bearer access token, refreshing if expired or forced."""
        if self.config.standalone_mode:
            return "panw-bearer-token-simulated-5g-sase"

        if self.config.auth_token:
            return self.config.auth_token

        # Check if cached token is still valid (with 60-second buffer)
        current_time = time.time()
        if (
            not force_refresh
            and self._cached_token
            and current_time < (self._token_expiry_timestamp - 60)
        ):
            return self._cached_token

        return self._fetch_oauth2_token()

    def _fetch_oauth2_token(self) -> str:
        """Request a new OAuth2 access token from PANW Auth Service."""
        self.config.validate()

        payload = {
            "grant_type": "client_credentials",
            "scope": f"tsg_id:{self.config.tsg_id}",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            response = requests.post(
                self.config.auth_url,
                data=payload,
                headers=headers,
                auth=(self.config.client_id, self.config.client_secret),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise ConnectionError(f"Failed to connect to PANW Auth Service at {self.config.auth_url}: {exc}") from exc

        if response.status_code != 200:
            error_details = response.text
            try:
                err_json = response.json()
                error_details = err_json.get("error_description") or err_json.get("error") or response.text
            except Exception:
                pass
            raise PermissionError(
                f"PANW OAuth2 Token request failed [HTTP {response.status_code}]: {error_details}"
            )

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise ValueError(f"Malformed token response, missing 'access_token': {data}")

        expires_in = int(data.get("expires_in", 900))  # Default 15 minutes
        self._cached_token = token
        self._token_expiry_timestamp = time.time() + expires_in

        return token

    def get_auth_headers(self, force_refresh: bool = False) -> dict:
        """Return HTTP headers with Bearer token authentication."""
        token = self.get_access_token(force_refresh=force_refresh)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
