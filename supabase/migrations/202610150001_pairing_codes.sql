-- =============================================================================
-- Migration: 202610150001_pairing_codes.sql
-- Adds the pairing_codes table that supports the secure desktop-pairing flow.
--
-- Additive only — no existing tables, columns, policies, or indexes are altered.
-- Safe to run on a database that does not yet have this table.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Add paired_at column to devices (records when a device was paired)
--    Additive: no effect on existing rows (defaults to NULL).
-- -----------------------------------------------------------------------------
ALTER TABLE public.devices
    ADD COLUMN IF NOT EXISTS paired_at TIMESTAMPTZ NULL;

-- -----------------------------------------------------------------------------
-- 2. pairing_codes table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pairing_codes (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id    UUID        NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
    code       TEXT        NOT NULL,
    is_used    BOOLEAN     NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    used_at    TIMESTAMPTZ NULL,
    device_id  UUID        NULL REFERENCES public.devices(id) ON DELETE SET NULL
);

-- Unique constraint: no two active rows may share the same code value.
-- Using a partial unique index only on unused codes avoids false conflicts
-- after a code has been consumed (the same 6-char string could theoretically
-- be reissued in a future session once the prior row is marked is_used=TRUE).
CREATE UNIQUE INDEX IF NOT EXISTS idx_pairing_codes_code_unused
    ON public.pairing_codes(code)
    WHERE NOT is_used;

-- Supporting indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_pairing_codes_home
    ON public.pairing_codes(home_id);

CREATE INDEX IF NOT EXISTS idx_pairing_codes_active
    ON public.pairing_codes(expires_at)
    WHERE NOT is_used;

-- -----------------------------------------------------------------------------
-- 3. Row-Level Security
-- -----------------------------------------------------------------------------
ALTER TABLE public.pairing_codes ENABLE ROW LEVEL SECURITY;

-- Home owners may LIST their own active codes (e.g. a "manage pairings" screen).
-- The claim endpoint uses the service-role admin client and bypasses RLS.
CREATE POLICY "Owners can view own pairing codes"
    ON public.pairing_codes FOR SELECT
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

-- Home owners may explicitly delete (revoke) their own codes.
CREATE POLICY "Owners can delete own pairing codes"
    ON public.pairing_codes FOR DELETE
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

-- INSERT and UPDATE are performed exclusively via the service-role admin client
-- (which bypasses RLS).  No authenticated-user INSERT policy is required or
-- desired — users never write to this table directly.

-- -----------------------------------------------------------------------------
-- Notes for the operator applying this migration
-- -----------------------------------------------------------------------------
-- 1. Apply via the Supabase SQL Editor or CLI:
--      supabase db push   (if using the local dev workflow)
--      or paste into Project > SQL Editor > Run
-- 2. The backend Python code uses the service-role admin client for all writes
--    and reads on pairing_codes, so no additional Supabase policies for the
--    anon/authenticated roles are needed for the claim endpoint.
-- 3. The partial unique index (idx_pairing_codes_code_unused) implements the
--    "code can be reused after expiry" semantic at the database level.
