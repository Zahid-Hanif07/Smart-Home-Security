"""Fail-closed access to OTTO's device credential in Windows Credential Manager."""
from __future__ import annotations

import importlib
import sys


SERVICE_NAME = "OTTO desktop camera"
USERNAME = "device credential"


class DeviceCredentialStoreError(RuntimeError):
    """Credential storage is unsupported or could not be accessed."""


class DeviceCredentialStore:
    """Read and write the paired device credential using Windows Credential Manager."""

    @staticmethod
    def _backend():
        if sys.platform != "win32":
            raise DeviceCredentialStoreError(
                "Device credentials are supported only by Windows Credential Manager."
            )

        try:
            keyring = importlib.import_module("keyring")
            windows_backend = importlib.import_module("keyring.backends.Windows")
            expected_type = windows_backend.WinVaultKeyring
            backend = keyring.get_keyring()
        except Exception:
            raise DeviceCredentialStoreError(
                "Windows Credential Manager support is unavailable."
            ) from None

        if type(backend) is not expected_type:
            raise DeviceCredentialStoreError(
                "The active keyring is not the Windows Credential Manager backend."
            )
        return backend

    def save(self, credential: str) -> None:
        if not isinstance(credential, str) or not credential:
            raise DeviceCredentialStoreError("A non-empty device credential is required.")
        try:
            self._backend().set_password(SERVICE_NAME, USERNAME, credential)
        except DeviceCredentialStoreError:
            raise
        except Exception:
            raise DeviceCredentialStoreError(
                "Windows Credential Manager could not save the device credential."
            ) from None

    def retrieve(self) -> str | None:
        try:
            credential = self._backend().get_password(SERVICE_NAME, USERNAME)
        except DeviceCredentialStoreError:
            raise
        except Exception:
            raise DeviceCredentialStoreError(
                "Windows Credential Manager could not read the device credential."
            ) from None
        if credential is not None and not isinstance(credential, str):
            raise DeviceCredentialStoreError(
                "Windows Credential Manager returned an invalid device credential."
            )
        return credential

    def delete(self) -> None:
        try:
            backend = self._backend()
            if backend.get_password(SERVICE_NAME, USERNAME) is not None:
                backend.delete_password(SERVICE_NAME, USERNAME)
        except DeviceCredentialStoreError:
            raise
        except Exception:
            raise DeviceCredentialStoreError(
                "Windows Credential Manager could not delete the device credential."
            ) from None
