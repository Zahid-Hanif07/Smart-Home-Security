"""Unauthenticated desktop claim client with secure one-time credential storage."""
from __future__ import annotations

import platform
import uuid
from dataclasses import dataclass
from typing import Callable

import httpx

from app.config.settings import API_BASE_URL
from app.security.device_credential_store import (
    DeviceCredentialStore,
)
from app.security.device_identity import get_or_create_device_identifier


class DevicePairingError(RuntimeError):
    """A safe, user-displayable pairing error with no response body or secret."""


class DeviceAlreadyRegisteredError(DevicePairingError):
    """The server recognizes the device but cannot reissue its credential."""


class DeviceCredentialProvisioningError(DevicePairingError):
    """The one-time claim succeeded but its credential could not be persisted."""


@dataclass(frozen=True)
class PairingResult:
    device_id: str
    home_id: str
    device_name: str


class DevicePairingService:
    """Claim a pairing code without sending homeowner authorization headers."""

    def __init__(
        self,
        *,
        api_base_url: str = API_BASE_URL,
        http_client: httpx.Client | None = None,
        credential_store: DeviceCredentialStore | None = None,
        device_identifier_provider: Callable[[], str] = get_or_create_device_identifier,
        device_name: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._claim_url = f"{api_base_url.rstrip('/')}/api/pairing/claim"
        self._http_client = http_client
        self._credential_store = (
            credential_store
            if credential_store is not None
            else DeviceCredentialStore()
        )
        self._device_identifier_provider = device_identifier_provider
        self._device_name = (device_name or platform.node() or "OTTO Desktop").strip()[:100]
        self._timeout = timeout

    def claim(self, code: str) -> PairingResult:
        clean_code = code.strip()
        if not clean_code:
            raise DevicePairingError("Enter the pairing code shown in the mobile app.")

        try:
            device_identifier = self._device_identifier_provider()
            uuid.UUID(device_identifier)
        except Exception:
            raise DevicePairingError(
                "The desktop's stable device identity is unavailable."
            ) from None

        if not self._device_name:
            raise DevicePairingError("The desktop name is unavailable.")

        try:
            # Confirm the Windows backend is reachable before consuming a
            # one-time code. The returned existing credential is discarded.
            self._credential_store.retrieve()
        except Exception:
            raise DevicePairingError(
                "Windows Credential Manager is unavailable; pairing was not attempted."
            ) from None

        payload = {
            "code": clean_code,
            "device_name": self._device_name,
            "device_identifier": device_identifier,
            "device_type": "desktop_camera",
        }
        try:
            if self._http_client is not None:
                response = self._http_client.post(self._claim_url, json=payload)
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(self._claim_url, json=payload)
        except httpx.HTTPError:
            raise DevicePairingError(
                "Could not reach the OTTO API. Check the connection and try again."
            ) from None

        if response.status_code != 200:
            if response.status_code in (404, 410):
                raise DevicePairingError(
                    "The pairing code is invalid or expired. Generate a fresh code in the mobile app."
                )
            if response.status_code == 422:
                raise DevicePairingError(
                    "The pairing code or desktop identity was rejected. Check the code and try again."
                )
            if response.status_code == 409:
                raise DevicePairingError(
                    "This desktop is already associated with another home. Contact support."
                )
            raise DevicePairingError(
                f"The OTTO API could not complete pairing (HTTP {response.status_code})."
            )

        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, TypeError):
            raise DevicePairingError(
                "The OTTO API returned an invalid pairing response."
            ) from None

        if data.get("status") == "already_registered":
            raise DeviceAlreadyRegisteredError(
                "This desktop is already registered. Its existing credential cannot be recovered through pairing."
            )
        if data.get("status") != "registered" or data.get("credential_already_issued") is True:
            raise DevicePairingError("The OTTO API did not confirm a new device registration.")

        try:
            device_id = str(uuid.UUID(str(data["device_id"])))
            home_id = str(uuid.UUID(str(data["home_id"])))
            response_name = data["device_name"]
            credential = data["device_token"]
            if (
                not isinstance(response_name, str)
                or not response_name
                or data.get("device_type") != "desktop_camera"
                or not isinstance(credential, str)
                or not credential
            ):
                raise ValueError
        except (KeyError, ValueError, TypeError):
            raise DeviceCredentialProvisioningError(
                "The server may have consumed the pairing code but returned incomplete credentials. "
                "Do not retry automatically; generate a fresh code and use a carefully reviewed recovery procedure."
            ) from None

        try:
            self._credential_store.save(credential)
        except Exception:
            raise DeviceCredentialProvisioningError(
                "The server consumed the pairing code, but Windows Credential Manager could not save the device credential. "
                "Do not retry this code. A fresh pairing code and a carefully reviewed recovery procedure may be required."
            ) from None
        finally:
            # Do not retain the one-time credential in the response mapping.
            data.pop("device_token", None)

        return PairingResult(
            device_id=device_id,
            home_id=home_id,
            device_name=response_name,
        )
