import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.security.device_credential_store import DeviceCredentialStoreError
from app.services.device_pairing_service import (
    DeviceAlreadyRegisteredError,
    DeviceCredentialProvisioningError,
    DevicePairingError,
    DevicePairingService,
)
from app.streaming import frame_publisher as frame_publisher_module
from app.streaming.frame_publisher import FramePublisher


DEVICE_IDENTIFIER = "05b2a8c5-1327-4edf-a31f-7ee73f5d0ca1"


class FakeCredentialStore:
    def __init__(self, credential=None, save_error=None):
        self.credential = credential
        self.save_error = save_error
        self.saved = []

    def retrieve(self):
        return self.credential

    def save(self, credential):
        if self.save_error is not None:
            raise self.save_error
        self.saved.append(credential)


def _claim_payload(**overrides):
    payload = {
        "device_id": str(uuid4()),
        "home_id": str(uuid4()),
        "device_name": "OTTO Test Desktop",
        "device_type": "desktop_camera",
        "status": "registered",
        "message": "registered",
        "device_token": "test-only-device-credential",
        "credential_already_issued": False,
    }
    payload.update(overrides)
    return payload


def _service_for_response(payload, *, status_code=200, store=None):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(status_code, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handle))
    service = DevicePairingService(
        api_base_url="http://test-api:8085/",
        http_client=client,
        credential_store=store or FakeCredentialStore(),
        device_identifier_provider=lambda: DEVICE_IDENTIFIER,
        device_name="OTTO Test Desktop",
    )
    return service, client, requests


def test_successful_claim_stores_credential_and_sends_exact_unauthenticated_payload():
    store = FakeCredentialStore()
    service, client, requests = _service_for_response(_claim_payload(), store=store)
    try:
        result = service.claim(" ABC-234 ")
    finally:
        client.close()

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url == "http://test-api:8085/api/pairing/claim"
    assert "authorization" not in request.headers
    assert json.loads(request.content) == {
        "code": "ABC-234",
        "device_name": "OTTO Test Desktop",
        "device_identifier": DEVICE_IDENTIFIER,
        "device_type": "desktop_camera",
    }
    assert store.saved == ["test-only-device-credential"]
    assert result.device_id
    assert result.home_id
    assert not hasattr(result, "device_token")


@pytest.mark.parametrize("status_code", [404, 410, 422])
def test_invalid_or_expired_code_does_not_store_credential(status_code):
    store = FakeCredentialStore()
    service, client, requests = _service_for_response(
        {"detail": "server detail is not shown"}, status_code=status_code, store=store
    )
    try:
        with pytest.raises(DevicePairingError):
            service.claim("ABC-234")
    finally:
        client.close()

    assert len(requests) == 1
    assert store.saved == []


def test_already_registered_without_credential_is_not_reported_as_paired():
    store = FakeCredentialStore()
    response = _claim_payload(
        status="already_registered",
        device_token=None,
        credential_already_issued=True,
    )
    service, client, requests = _service_for_response(response, store=store)
    try:
        with pytest.raises(DeviceAlreadyRegisteredError, match="cannot be recovered"):
            service.claim("ABC-234")
    finally:
        client.close()

    assert len(requests) == 1
    assert store.saved == []


def test_storage_failure_reports_consumed_code_without_retry_or_credential_leak():
    credential = "test-only-device-credential"
    store = FakeCredentialStore(save_error=DeviceCredentialStoreError(credential))
    service, client, requests = _service_for_response(_claim_payload(), store=store)
    try:
        with pytest.raises(DeviceCredentialProvisioningError) as error:
            service.claim("ABC-234")
    finally:
        client.close()

    assert "consumed" in str(error.value)
    assert credential not in str(error.value)
    assert error.value.__cause__ is None
    assert len(requests) == 1


def test_missing_credential_store_fails_before_claim_request():
    store = FakeCredentialStore(save_error=DeviceCredentialStoreError("unavailable"))
    store.retrieve = lambda: (_ for _ in ()).throw(DeviceCredentialStoreError("unavailable"))
    service, client, requests = _service_for_response(_claim_payload(), store=store)
    try:
        with pytest.raises(DevicePairingError, match="pairing was not attempted"):
            service.claim("ABC-234")
    finally:
        client.close()

    assert requests == []
    assert store.saved == []


def test_frame_publisher_loads_from_store_and_fails_closed_without_fallback(monkeypatch):
    class StoreWithCredential:
        def retrieve(self):
            return "test-only-device-credential"

    monkeypatch.setattr(
        frame_publisher_module, "DeviceCredentialStore", StoreWithCredential
    )
    publisher = FramePublisher(home_id=str(uuid4()))
    assert publisher.device_token == "test-only-device-credential"

    class BrokenStore:
        def retrieve(self):
            raise DeviceCredentialStoreError("unavailable")

    monkeypatch.setattr(frame_publisher_module, "DeviceCredentialStore", BrokenStore)
    monkeypatch.setattr(
        frame_publisher_module.settings,
        "DEVICE_CREDENTIAL",
        SecretStr("must-not-be-used-as-fallback"),
    )
    unavailable_publisher = FramePublisher(home_id=str(uuid4()))
    assert unavailable_publisher.device_token is None


def test_frame_publisher_preserves_explicit_test_credential_injection(monkeypatch):
    class StoreMustNotBeUsed:
        def __init__(self):
            raise AssertionError("explicit injection should bypass store retrieval")

    monkeypatch.setattr(
        frame_publisher_module, "DeviceCredentialStore", StoreMustNotBeUsed
    )
    publisher = FramePublisher(home_id=str(uuid4()), device_token="injected-test-credential")

    assert publisher.device_token == "injected-test-credential"
