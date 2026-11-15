import sys
import types
from uuid import UUID

import pytest

from app.security import device_credential_store
from app.security.device_credential_store import (
    DeviceCredentialStore,
    DeviceCredentialStoreError,
    SERVICE_NAME,
    USERNAME,
)


class FakeWindowsCredentialManager:
    """In-memory stand-in; no test accesses the developer's real keyring."""

    def __init__(self):
        self.values = {}

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def get_password(self, service, username):
        return self.values.get((service, username))

    def delete_password(self, service, username):
        del self.values[(service, username)]


FakeWindowsCredentialManager.__module__ = "keyring.backends.Windows"


@pytest.fixture
def fake_windows_keyring(monkeypatch):
    backend = FakeWindowsCredentialManager()
    keyring_module = types.ModuleType("keyring")
    keyring_module.get_keyring = lambda: backend
    windows_module = types.ModuleType("keyring.backends.Windows")
    windows_module.WinVaultKeyring = FakeWindowsCredentialManager
    monkeypatch.setitem(sys.modules, "keyring", keyring_module)
    monkeypatch.setitem(sys.modules, "keyring.backends.Windows", windows_module)
    monkeypatch.setattr(device_credential_store.sys, "platform", "win32")
    return backend


def test_store_round_trip_uses_explicit_windows_backend(fake_windows_keyring):
    store = DeviceCredentialStore()
    credential = "test-device-credential"

    store.save(credential)
    assert fake_windows_keyring.values[(SERVICE_NAME, USERNAME)] == credential
    assert store.retrieve() == credential

    store.delete()
    assert store.retrieve() is None


def test_store_fails_closed_on_unsupported_platform(monkeypatch):
    monkeypatch.setattr(device_credential_store.sys, "platform", "linux")

    with pytest.raises(DeviceCredentialStoreError, match="only by Windows"):
        DeviceCredentialStore().retrieve()


def test_store_fails_closed_if_keyring_selects_another_backend(
    fake_windows_keyring, monkeypatch
):
    import keyring

    class OtherBackend:
        pass

    monkeypatch.setattr(keyring, "get_keyring", OtherBackend)

    with pytest.raises(DeviceCredentialStoreError, match="not the Windows"):
        DeviceCredentialStore().retrieve()


def test_store_fails_closed_if_windows_backend_is_missing(
    fake_windows_keyring, monkeypatch
):
    original_import = device_credential_store.importlib.import_module

    def import_without_windows_backend(name):
        if name == "keyring.backends.Windows":
            raise ImportError("backend unavailable")
        return original_import(name)

    monkeypatch.setattr(
        device_credential_store.importlib, "import_module", import_without_windows_backend
    )

    with pytest.raises(DeviceCredentialStoreError, match="support is unavailable"):
        DeviceCredentialStore().retrieve()


def test_store_errors_do_not_include_credential_value(fake_windows_keyring):
    credential = "test-device-credential"

    def fail_save(*_args):
        raise RuntimeError(credential)

    fake_windows_keyring.set_password = fail_save
    with pytest.raises(DeviceCredentialStoreError) as error:
        DeviceCredentialStore().save(credential)

    assert credential not in str(error.value)
    assert error.value.__cause__ is None


def test_stable_device_identifier_is_saved_once_and_reused(tmp_path, monkeypatch):
    from app.security import device_identity

    monkeypatch.setattr(device_identity.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    first = device_identity.get_or_create_device_identifier()
    second = device_identity.get_or_create_device_identifier()

    assert first == second
    assert str(UUID(first)) == first
    assert (tmp_path / "OTTO" / "device_identifier").read_text() == first


def test_corrupt_stable_identifier_fails_without_regenerating(tmp_path, monkeypatch):
    from app.security import device_identity

    monkeypatch.setattr(device_identity.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    identifier_file = tmp_path / "OTTO" / "device_identifier"
    identifier_file.parent.mkdir()
    identifier_file.write_text("invalid")

    with pytest.raises(device_identity.DeviceIdentityError):
        device_identity.get_or_create_device_identifier()

    assert identifier_file.read_text() == "invalid"
