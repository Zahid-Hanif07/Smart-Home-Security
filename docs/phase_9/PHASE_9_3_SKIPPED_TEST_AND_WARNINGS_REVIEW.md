# Phase 9.3 — Skipped Test and Warnings Review

Status: **PASS**

## Scope and safety

This was a read-only diagnostic review. No tests were rerun, no files were
modified other than this report, and no warning filters or environment values
were changed.

No webcam, FastAPI server, Flutter application, Supabase service, external
network, model, database, or credential was accessed.

## Worktree status

The worktree remains heavily modified from earlier phases. Existing modified
and untracked files were preserved. No reset, clean, stash, checkout, or
overwrite operation was used.

The only file created by this phase is:

- `docs/phase_9/PHASE_9_3_SKIPPED_TEST_AND_WARNINGS_REVIEW.md`

Phase 9.2 and Phase 9.1 reports remain present and were inspected:

- `docs/phase_9/PHASE_9_2_DESKTOP_BACKEND_STABILITY_BASELINE.md`
- `docs/phase_9/PHASE_9_1_DESKTOP_CAMERA_LIFECYCLE_TESTS.md`

## Exact skipped test

The single skip reported by Phase 9.2 is:

- File: `tests/test_step11_repositories.py`
- Test class: `TestRepositoryIntegration`
- Test method: `test_12_real_supabase_write_survives_a_fresh_list_read`
- Source location: approximately line 202

The test skips when any of these conditions is true:

```python
os.getenv("RUN_LIVE_SUPABASE_TESTS") != "1"
or not is_supabase_configured()
or SupabaseClientManager.get_admin_client() is None
```

Skip reason recorded by the test:

> Requires explicitly enabled Supabase integration settings and service-role access.

This is intentional for the Phase 9.2 isolated baseline. Running it would
perform a real `POST /api/homes/initial` and subsequent reads against
Supabase, so it was correctly not executed in this phase. It is not a local
offline regression test.

## Warning investigation

| Warning | Verified origin | Scope | Impact | Recommended future action |
|---|---|---|---|---|
| `StarletteDeprecationWarning` about `httpx` test-client integration | Installed dependency: `.venv/Lib/site-packages/fastapi/testclient.py:1` re-exports Starlette's `TestClient`; the warning is emitted by the installed Starlette/FastAPI test-client stack | Test tooling only | Does not affect application runtime routes; future dependency changes may require the newer client integration | Plan a dependency-compatibility update after checking the project's supported FastAPI/Starlette/httpx versions |
| Supabase `timeout` and `verify` deprecations | Installed dependency `.venv/Lib/site-packages/supabase/_sync/client.py:309` passes those arguments into its PostgREST client; the project entry point is `app/database/supabase_client.py:17` / `:36`, where `create_client()` is called | Test initialization/fallback path; dependency API compatibility | Current tests still pass; a future supabase/postgrest release may remove or change those arguments | Upgrade dependencies only as a planned maintenance task, then retest the Supabase client construction path |
| `InsecureKeyLengthWarning` | Test source `tests/test_backend.py:202-205` uses the literal test-only tampered JWT key `"wrong_signature_secret"`; PyJWT emits the warning from its encode path | Test fixture only | Does not weaken production credentials; it makes the negative-test fixture noisier and less representative of recommended HMAC key length | Replace the negative-test fixture with a non-production key of recommended length in a separate test-maintenance task, without exposing or changing real secrets |
| `PytestCacheWarning` for `D:\.pytest_cache\v\cache` / `WinError 183` | Installed dependency `.venv/Lib/site-packages/_pytest/cacheprovider.py:423` and `:469` attempt to write pytest cache entries; read-only inspection showed the parent `D:\.pytest_cache` exists, while access to descendants is denied | Local test environment/cache only | Does not affect test assertions or application runtime, but prevents pytest from persisting cache metadata | Investigate the D: drive cache ACL/path ownership or configure an approved writable pytest cache location in a separate environment task; do not delete or alter it during this audit |

## Confirmed facts and unresolved questions

### Confirmed

- The one skipped test is a deliberate live-Supabase integration guard.
- It requires `RUN_LIVE_SUPABASE_TESTS=1`, configured Supabase settings, and an
  available admin client.
- It was safe and correct not to run it under the Phase 9.2 restrictions.
- The Starlette/httpx warning is dependency-originated.
- The Supabase warning is dependency-originated but reached through the
  project's centralized Supabase client factory.
- The short-key JWT warning originates from a test literal, not from a stored
  production credential.
- The pytest cache warning is emitted by pytest's cache plugin and is unrelated
  to application logic.

### Unresolved or not established

- The exact dependency versions that will remove the Starlette/httpx warning
  are not established and should not be guessed.
- The future Supabase/PostgREST replacement API for `timeout` and `verify` was
  not researched or changed.
- The reason pytest selected `D:\.pytest_cache` rather than a project-local
  cache path was not established from the Phase 9.2 output. No project pytest
  configuration file was found during this inspection, and the inaccessible
  descendant path prevented deeper ACL inspection.
- No live Supabase connectivity or service-role permission was tested.

## Phase 9.2 baseline validity

Phase 9.2 remains a valid **offline** desktop/backend baseline:

- 309 tests passed.
- 1 intentionally guarded live-Supabase test was skipped.
- 0 tests failed.
- The warnings are non-failing and their origins are understood sufficiently
  for tracking.

The baseline must not be interpreted as proof of live Supabase behavior,
physical-camera behavior, Flutter behavior, or production dependency
compatibility.

## Recommended future actions

1. Keep `test_12_real_supabase_write_survives_a_fresh_list_read` outside offline
   CI unless a separately authorized live integration environment is provided.
2. Track the Starlette/httpx and Supabase warnings during planned dependency
   maintenance; do not make ad-hoc upgrades.
3. Update the test-only short JWT key in a separate test cleanup change if a
   warning-free suite is required.
4. Have the environment owner resolve the protected pytest cache path or
   provide a writable cache directory, without deleting existing data.
5. Preserve the current Phase 9.2 results as the offline regression baseline.

## Final safety confirmation

- No existing project file was modified.
- No application, test, configuration, dependency, credential, model, or
  database state was changed.
- No test was rerun in this phase.
- No webcam or external service was started.
