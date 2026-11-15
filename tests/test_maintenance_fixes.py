"""
Targeted tests for the two maintenance fixes applied before Phase 3.

Test A — BackendStore.clear() now resets pairing state
Test B — is_memory_fallback_enabled() raises RuntimeError when
          TEST_ISOLATED_MODE=1 AND ENVIRONMENT=production
Test C — ENVIRONMENT validator rejects unknown values

Run with:
    TEST_ISOLATED_MODE=1 python -m pytest tests/test_maintenance_fixes.py -v
"""
from __future__ import annotations

import os

os.environ.setdefault("TEST_ISOLATED_MODE", "1")

import pytest


# ---------------------------------------------------------------------------
# Test A: BackendStore.clear() resets pairing_repository
# ---------------------------------------------------------------------------

class TestBackendStoreClearIncludesPairing:
    """After BackendStore.clear(), pairing in-memory state must be empty."""

    def setup_method(self):
        from app.services.backend_store import backend_store
        from app.repositories.pairing_repository import pairing_repository
        backend_store.clear()
        pairing_repository.clear()

    def teardown_method(self):
        from app.services.backend_store import backend_store
        from app.repositories.pairing_repository import pairing_repository
        backend_store.clear()
        pairing_repository.clear()

    def test_clear_removes_in_memory_pairing_codes(self):
        """Codes inserted before clear() must not survive clear()."""
        from datetime import datetime, timedelta, timezone
        from uuid import UUID, uuid4
        from app.repositories.pairing_repository import pairing_repository

        home_id = uuid4()
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)
        pairing_repository.create_code(home_id=home_id, code="CLRTEST", expires_at=expires)

        # Verify the code is there
        assert "CLRTEST" in pairing_repository._in_memory_codes

        # Call the unified BackendStore.clear()
        from app.services.backend_store import backend_store
        backend_store.clear()

        # Code must be gone
        assert "CLRTEST" not in pairing_repository._in_memory_codes, (
            "BackendStore.clear() did not reset pairing_repository codes"
        )

    def test_clear_removes_in_memory_pairing_devices(self):
        """Devices created by a claim before clear() must not survive clear()."""
        from datetime import datetime, timedelta, timezone
        from uuid import uuid4
        from app.repositories.pairing_repository import pairing_repository

        home_id = uuid4()
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)
        pairing_repository.create_code(home_id=home_id, code="CLRDEV1", expires_at=expires)
        pairing_repository.claim_code(
            code="CLRDEV1",
            device_name="Clearable PC",
            device_type="desktop_camera",
            device_identifier="clear-device-id",
        )

        # Verify device was created
        assert len(pairing_repository._in_memory_devices) == 1

        from app.services.backend_store import backend_store
        backend_store.clear()

        assert len(pairing_repository._in_memory_devices) == 0, (
            "BackendStore.clear() did not reset pairing_repository devices"
        )

    def test_pairing_state_does_not_leak_across_tests(self):
        """State created in one test method must not be visible in the next.

        This test verifies that setup_method's backend_store.clear() call
        was sufficient — no code from a previous test should survive.
        """
        from app.repositories.pairing_repository import pairing_repository
        assert len(pairing_repository._in_memory_codes) == 0, (
            "Pairing codes leaked from a previous test — BackendStore.clear() not working"
        )
        assert len(pairing_repository._in_memory_devices) == 0, (
            "Pairing devices leaked from a previous test — BackendStore.clear() not working"
        )

    def test_other_repos_also_still_cleared(self):
        """Confirm the BackendStore.clear() change did not break other repos."""
        from app.repositories import home_repository, device_repository

        # Verify they are empty after clear (setup_method called clear already)
        assert len(home_repository._in_memory_homes) == 0
        assert len(device_repository._in_memory_devices) == 0


# ---------------------------------------------------------------------------
# Test B: is_memory_fallback_enabled() blocks ENVIRONMENT=production
# ---------------------------------------------------------------------------

class TestMemoryFallbackProductionGuard:
    """Verify the production guard raises RuntimeError correctly."""

    def test_development_environment_allows_fallback(self, monkeypatch):
        """ENVIRONMENT=development + TEST_ISOLATED_MODE=1 → returns True (tests allowed)."""
        monkeypatch.setenv("TEST_ISOLATED_MODE", "1")
        import app.config.backend_settings as _settings_mod
        original_env = _settings_mod.settings.ENVIRONMENT
        _settings_mod.settings.ENVIRONMENT = "development"
        try:
            from app.repositories.home_repository import is_memory_fallback_enabled
            result = is_memory_fallback_enabled()
            assert result is True, "Development + TEST_ISOLATED_MODE=1 should return True"
        finally:
            _settings_mod.settings.ENVIRONMENT = original_env

    def test_staging_environment_allows_fallback(self, monkeypatch):
        """ENVIRONMENT=staging + TEST_ISOLATED_MODE=1 → returns True."""
        monkeypatch.setenv("TEST_ISOLATED_MODE", "1")
        import app.config.backend_settings as _settings_mod
        original_env = _settings_mod.settings.ENVIRONMENT
        _settings_mod.settings.ENVIRONMENT = "staging"
        try:
            from app.repositories.home_repository import is_memory_fallback_enabled
            result = is_memory_fallback_enabled()
            assert result is True, "Staging + TEST_ISOLATED_MODE=1 should return True"
        finally:
            _settings_mod.settings.ENVIRONMENT = original_env

    def test_production_environment_blocks_fallback(self, monkeypatch):
        """ENVIRONMENT=production + TEST_ISOLATED_MODE=1 → raises RuntimeError."""
        monkeypatch.setenv("TEST_ISOLATED_MODE", "1")
        import app.config.backend_settings as _settings_mod
        original_env = _settings_mod.settings.ENVIRONMENT
        _settings_mod.settings.ENVIRONMENT = "production"
        try:
            from app.repositories.home_repository import is_memory_fallback_enabled
            with pytest.raises(RuntimeError, match="TEST_ISOLATED_MODE=1 is not permitted"):
                is_memory_fallback_enabled()
        finally:
            _settings_mod.settings.ENVIRONMENT = original_env

    def test_no_isolated_mode_returns_false(self, monkeypatch):
        """Without TEST_ISOLATED_MODE=1, fallback is always False regardless of ENVIRONMENT."""
        monkeypatch.delenv("TEST_ISOLATED_MODE", raising=False)
        from app.repositories.home_repository import is_memory_fallback_enabled
        result = is_memory_fallback_enabled()
        assert result is False



# ---------------------------------------------------------------------------
# Test C: BackendSettings ENVIRONMENT validator
# ---------------------------------------------------------------------------

class TestEnvironmentValidator:
    """ENVIRONMENT field in BackendSettings must reject unknown values."""

    def test_valid_values_accepted(self):
        from app.config.backend_settings import BackendSettings
        for valid in ("development", "staging", "production"):
            s = BackendSettings(ENVIRONMENT=valid)
            assert s.ENVIRONMENT == valid

    def test_mixed_case_normalised(self):
        from app.config.backend_settings import BackendSettings
        s = BackendSettings(ENVIRONMENT="Production")
        assert s.ENVIRONMENT == "production"

    def test_unknown_value_raises(self):
        from pydantic import ValidationError
        from app.config.backend_settings import BackendSettings
        with pytest.raises((ValidationError, ValueError)):
            BackendSettings(ENVIRONMENT="demo")

    def test_default_is_development(self):
        """Default environment must be development (safe for local use)."""
        from app.config.backend_settings import BackendSettings
        s = BackendSettings(
            SUPABASE_URL="https://demo-project.supabase.co",
            ENVIRONMENT="development",
        )
        assert s.ENVIRONMENT == "development"
