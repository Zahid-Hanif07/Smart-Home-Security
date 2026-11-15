-- Additive migration: preserve all homes and designate one existing home per
-- owner as their initial home. New accounts may then safely retry setup.
ALTER TABLE public.homes
    ADD COLUMN IF NOT EXISTS is_initial BOOLEAN NOT NULL DEFAULT FALSE;

WITH first_home AS (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY owner_id ORDER BY created_at NULLS LAST, id) AS row_number
    FROM public.homes
)
UPDATE public.homes AS homes
SET is_initial = TRUE
FROM first_home
WHERE homes.id = first_home.id
  AND first_home.row_number = 1
  AND NOT EXISTS (
      SELECT 1 FROM public.homes AS marked
      WHERE marked.owner_id = homes.owner_id AND marked.is_initial
  );

CREATE UNIQUE INDEX IF NOT EXISTS idx_homes_one_initial_per_owner
    ON public.homes(owner_id)
    WHERE is_initial;

-- Permit selecting the flag from owner-authorized home rows; no change to the
-- existing RLS policies is required because they scope the whole row.
