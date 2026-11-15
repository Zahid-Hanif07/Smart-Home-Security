"""FastAPI routes for the desktop-pairing flow.

Two routers are defined here and registered separately in routes/__init__.py:

  homes_pairing_router   — nested under /api/homes/{home_id}/pairing-codes
                           Requires authenticated home owner.

  pairing_router         — mounted at /api/pairing
                           The /claim endpoint is intentionally unauthenticated:
                           the one-time code IS the credential.  All other
                           endpoints under this router require a valid user JWT.

Security decisions
------------------
* Ownership verification for code generation uses the existing
  ``home_repository.get_home_by_id(home_id, user_id)`` pattern — the same
  check used by every other home-scoped endpoint.  A 403 is raised
  automatically if the authenticated user does not own the home.

* The /claim endpoint receives no Authorization header.  It validates the
  code, resolves the home exclusively from the stored code record, and
  registers the device.  It does NOT issue any bearer token (Phase 3 scope).

* Rate limiting is enforced at the service layer (max active codes per home).
  The existing ``RequestRateLimitMiddleware`` applies its per-IP limit on top.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user_id
from app.models.pairing import PairingClaimRequest, PairingClaimResponse, PairingCodeResponse
from app.repositories.home_repository import home_repository
from app.services.pairing_service import pairing_service

# ---------------------------------------------------------------------------
# Router 1 — Authenticated, nested under homes
# ---------------------------------------------------------------------------

homes_pairing_router = APIRouter()


@homes_pairing_router.post(
    "",
    response_model=PairingCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a one-time pairing code for a home",
    description=(
        "Generates a cryptographically secure, human-readable 6-character code "
        "that a desktop application can use to pair with this home.  "
        "The code expires in 5 minutes and can only be used once.  "
        "A maximum of 5 active codes may exist per home at any time."
    ),
)
def generate_pairing_code(
    home_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> PairingCodeResponse:
    """POST /api/homes/{home_id}/pairing-codes

    Requires: valid Bearer token for a user who owns ``home_id``.
    Returns:  code, home_id, expires_at, ttl_seconds.
    """
    # Ownership check: raises 404 if home not found, 403 if not owned by user.
    home_repository.get_home_by_id(home_id, user_id)

    result = pairing_service.generate_code(
        home_id=home_id,
        requesting_user_id=user_id,
    )
    return PairingCodeResponse(**result)


# ---------------------------------------------------------------------------
# Router 2 — Pairing operations (claim is unauthenticated)
# ---------------------------------------------------------------------------

pairing_router = APIRouter()


@pairing_router.post(
    "/claim",
    response_model=PairingClaimResponse,
    status_code=status.HTTP_200_OK,
    summary="Claim a pairing code and register a desktop device",
    description=(
        "Called by the desktop application after the user displays a pairing code "
        "in the mobile app.  No Authorization header is required — the one-time "
        "code is the credential.  The home is resolved from the server-side code "
        "record; the client cannot supply or override the home_id.  "
        "No bearer token is issued in this phase."
    ),
)
def claim_pairing_code(body: PairingClaimRequest) -> PairingClaimResponse:
    """POST /api/pairing/claim

    Unauthenticated endpoint.  The one-time code is the sole credential.
    Returns device_id, home_id, status ('registered' or 'already_registered').
    Does NOT return a bearer token — token issuance is Phase 3 scope.
    """
    result = pairing_service.claim_code(
        # code is already normalised (hyphen stripped, uppercase) by the validator
        code=body.code,
        device_name=body.device_name,
        device_type=body.device_type,
        device_identifier=body.device_identifier,
    )
    return PairingClaimResponse(**result)
