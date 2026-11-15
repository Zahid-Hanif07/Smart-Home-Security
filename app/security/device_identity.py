"""Persistent, non-secret identifier for this Windows desktop installation."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import UUID, uuid4


class DeviceIdentityError(RuntimeError):
    """The stable desktop identifier could not be read or persisted."""


def get_or_create_device_identifier() -> str:
    """Return the identifier saved under this Windows user's Local AppData."""
    if sys.platform != "win32":
        raise DeviceIdentityError("Desktop device identity is supported only on Windows.")

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise DeviceIdentityError("Windows Local AppData is unavailable.")

    identifier_path = Path(local_app_data) / "OTTO" / "device_identifier"
    try:
        identifier_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with identifier_path.open("x", encoding="ascii") as identifier_file:
                identifier_file.write(str(uuid4()))
                identifier_file.flush()
                os.fsync(identifier_file.fileno())
        except FileExistsError:
            pass

        identifier = identifier_path.read_text(encoding="ascii").strip()
        return str(UUID(identifier))
    except Exception as exc:
        raise DeviceIdentityError(
            "The stable desktop identifier could not be read or saved."
        ) from exc
