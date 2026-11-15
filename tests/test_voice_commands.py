import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

os.environ.setdefault("TEST_ISOLATED_MODE", "1")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.main import app
from app.models.voice_command import VoiceCommandCreate
from app.repositories.voice_command_repository import VoiceCommandRepository
from app.repositories.home_repository import home_repository
import app.repositories.voice_command_repository as repository_module


client = TestClient(app)
MIGRATION_SQL = Path(__file__).parents[1] / "supabase" / "migrations" / "202611100001_voice_light_commands.sql"
OUTBOX_MIGRATION_SQL = Path(__file__).parents[1] / "supabase" / "migrations" / "202611100002_voice_command_outbox_worker.sql"


def _home(owner_id):
    home_id = uuid4()
    home_repository._in_memory_homes[home_id] = {
        "id": home_id,
        "owner_id": owner_id,
        "name": "Test Home",
        "address": None,
    }
    return home_id


def test_command_routes_require_homeowner_jwt():
    home_id = uuid4()
    response = client.post(
        f"/api/homes/{home_id}/commands",
        json={
            "client_command_id": str(uuid4()),
            "command": "all_lights_on",
            "target_type": "all_lights",
        },
    )
    assert response.status_code == 401


def test_only_four_command_names_are_accepted():
    with pytest.raises(ValidationError):
        VoiceCommandCreate(
            client_command_id=uuid4(),
            command="unlock_door",
            target_type="all_lights",
        )


def test_semantic_hash_excludes_device_snapshot():
    semantic = {
        "command": "all_lights_on",
        "target_type": "all_lights",
        "room_id": None,
    }
    same_request = dict(semantic)
    assert VoiceCommandRepository.request_hash(semantic) == VoiceCommandRepository.request_hash(same_request)


@pytest.mark.parametrize("command", ["light_on", "light_off"])
def test_room_commands_have_actual_device_count_and_retry_count(command):
    owner_id = uuid4()
    home_id = _home(owner_id)
    repository = VoiceCommandRepository()
    repository.seed_in_memory_eligible_devices(home_id, [uuid4(), uuid4(), uuid4()])
    data = {
        "client_command_id": uuid4(),
        "command": command,
        "target_type": "room",
        "room_id": uuid4(),
    }
    first = repository.create(home_id, owner_id, data)
    retry = repository.create(home_id, owner_id, data)
    assert first["device_count"] == 3
    assert retry["device_count"] == 3
    assert retry["command"]["device_count"] == 3


def test_different_semantic_request_with_same_key_returns_409():
    owner_id = uuid4()
    home_id = _home(owner_id)
    repository = VoiceCommandRepository()
    repository.seed_in_memory_eligible_devices(home_id, [uuid4()])
    client_id = uuid4()
    repository.create(home_id, owner_id, {
        "client_command_id": client_id,
        "command": "light_on",
        "target_type": "room",
        "room_id": uuid4(),
    })
    with pytest.raises(Exception) as error:
        repository.create(home_id, owner_id, {
            "client_command_id": client_id,
            "command": "light_off",
            "target_type": "room",
            "room_id": uuid4(),
        })
    assert error.value.status_code == 409


@pytest.mark.parametrize(
    ("command", "target_type", "room_id"),
    [
        ("light_on", "all_lights", None),
        ("light_off", "all_lights", None),
        ("all_lights_on", "room", uuid4()),
        ("all_lights_off", "room", uuid4()),
    ],
)
def test_mismatched_command_target_is_rejected(command, target_type, room_id):
    with pytest.raises(ValidationError):
        VoiceCommandCreate(
            client_command_id=uuid4(),
            command=command,
            target_type=target_type,
            room_id=room_id,
        )


@pytest.mark.parametrize(
    ("command", "target_type", "room_id"),
    [
        ("light_on", "room", uuid4()),
        ("light_off", "room", uuid4()),
        ("all_lights_on", "all_lights", None),
        ("all_lights_off", "all_lights", None),
    ],
)
def test_matching_command_target_is_accepted(command, target_type, room_id):
    parsed = VoiceCommandCreate(
        client_command_id=uuid4(),
        command=command,
        target_type=target_type,
        room_id=room_id,
    )
    assert parsed.command.value == command


def test_room_id_is_required_and_all_lights_room_id_is_forbidden():
    with pytest.raises(ValidationError):
        VoiceCommandCreate(
            client_command_id=uuid4(), command="light_on", target_type="room"
        )
    with pytest.raises(ValidationError):
        VoiceCommandCreate(
            client_command_id=uuid4(),
            command="all_lights_on",
            target_type="all_lights",
            room_id=uuid4(),
        )


def test_supabase_existing_response_preserves_device_count(monkeypatch):
    class Response:
        data = {
            "command": {"id": str(uuid4())},
            "existing": True,
            "device_count": 4,
        }

        def execute(self):
            return self

    class RpcClient:
        def rpc(self, name, params):
            assert name == "create_voice_command"
            return Response()

    monkeypatch.setattr(repository_module, "is_supabase_configured", lambda: True)
    monkeypatch.setattr(repository_module, "is_memory_fallback_enabled", lambda: False)
    monkeypatch.setattr(repository_module.SupabaseClientManager, "get_admin_client", lambda: RpcClient())
    repository = VoiceCommandRepository()
    result = repository.create(uuid4(), uuid4(), {
        "client_command_id": uuid4(),
        "command": "all_lights_on",
        "target_type": "all_lights",
        "room_id": None,
    })
    assert result["existing"] is True
    assert result["device_count"] == 4


def test_migration_serializes_capability_registration_on_device_row():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    capability_fn = sql.split("CREATE OR REPLACE FUNCTION public.validate_light_capability_room()", 1)[1]
    capability_fn = capability_fn.split("CREATE OR REPLACE FUNCTION public.validate_device_light_room()", 1)[0]
    assert "FROM public.devices" in capability_fn
    assert "FOR UPDATE" in capability_fn
    assert "light_control_requires_room" in capability_fn


def test_migration_serializes_room_changes_on_capability_rows():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    device_fn = sql.split("CREATE OR REPLACE FUNCTION public.validate_device_light_room()", 1)[1]
    device_fn = device_fn.split("DROP TRIGGER IF EXISTS device_capabilities_require_room", 1)[0]
    assert "FROM public.device_capabilities" in device_fn
    assert "device row lock" in device_fn
    assert "light_control_requires_room" in device_fn


def test_migration_checks_new_expiry_after_idempotency_lookup():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    existing_lookup = sql.index("SELECT * INTO v_existing")
    expiry_check = sql.index("invalid_command_expiry")
    server_expiry = sql.index("v_expires_at := v_now + interval '5 minutes'")
    assert existing_lookup < expiry_check < server_expiry


def test_migration_rejects_null_and_blank_hash_before_idempotency_lookup():
    sql = MIGRATION_SQL.read_text(encoding="utf-8")
    hash_check = sql.index("IF p_request_hash IS NULL")
    existing_lookup = sql.index("SELECT * INTO v_existing")
    hash_guard = sql[hash_check:existing_lookup]
    assert "pg_catalog.btrim(p_request_hash) = ''" in hash_guard
    assert "invalid_request_hash" in hash_guard
    assert "USING ERRCODE = '22023'" in hash_guard


def test_outbox_migration_uses_shared_status_refresh_everywhere():
    sql = OUTBOX_MIGRATION_SQL.read_text(encoding="utf-8")
    claim = sql.split("CREATE OR REPLACE FUNCTION public.claim_voice_command_outbox", 1)[1]
    claim = claim.split("CREATE OR REPLACE FUNCTION public.refresh_voice_command_status", 1)[0]
    recovery = sql.split("CREATE OR REPLACE FUNCTION public.recover_voice_command_outbox", 1)[1]
    recovery = recovery.split("CREATE OR REPLACE FUNCTION public.complete_voice_command_outbox", 1)[0]
    completion = sql.split("CREATE OR REPLACE FUNCTION public.complete_voice_command_outbox", 1)[1]
    assert "PERFORM public.refresh_voice_command_status" in claim
    assert "PERFORM public.refresh_voice_command_status" in recovery
    assert "PERFORM public.refresh_voice_command_status" in completion
    assert "v_total INTEGER" not in completion


def test_outbox_completion_requires_a_live_lease():
    sql = OUTBOX_MIGRATION_SQL.read_text(encoding="utf-8")
    completion = sql.split("CREATE OR REPLACE FUNCTION public.complete_voice_command_outbox", 1)[1]
    assert "AND o.lease_expires_at > pg_catalog.now()" in completion
    assert "RAISE EXCEPTION 'stale_lease'" in completion
