-- Phase 10.4C-A: transactional outbox worker RPCs.
-- These functions are additive and are not executed by application startup.
-- Adapter work must happen outside the transaction opened by each RPC.

CREATE OR REPLACE FUNCTION public.claim_voice_command_outbox(
    p_worker_id TEXT,
    p_limit INTEGER DEFAULT 10,
    p_lease_seconds INTEGER DEFAULT 60
)
RETURNS SETOF JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_candidate RECORD;
    v_job RECORD;
BEGIN
    IF p_limit < 1 OR p_limit > 100 THEN
        RAISE EXCEPTION 'invalid_limit' USING ERRCODE = '22023';
    END IF;
    IF p_lease_seconds < 1 OR p_lease_seconds > 300 THEN
        RAISE EXCEPTION 'invalid_lease_seconds' USING ERRCODE = '22023';
    END IF;

    -- ORDER BY is deterministic candidate ordering, not a lock-order guarantee.
    -- The explicit locks below establish home -> room -> device ordering.
    FOR v_candidate IN
        SELECT o.id AS outbox_id, o.command_id, o.home_id, o.device_id,
               r.id AS result_id, c.room_id
        FROM public.command_outbox o
        JOIN public.command_device_results r
          ON r.id = o.command_device_result_id
         AND r.command_id = o.command_id
         AND r.home_id = o.home_id
         AND r.device_id = o.device_id
        JOIN public.voice_commands c
          ON c.id = o.command_id AND c.home_id = o.home_id
        WHERE o.state = 'pending'
          AND o.next_attempt_at <= pg_catalog.now()
          AND c.expires_at > pg_catalog.now()
          AND r.attempt_count < 5
        ORDER BY o.home_id, o.device_id, r.id, o.id
        LIMIT p_limit
    LOOP
        PERFORM 1 FROM public.homes
        WHERE id = v_candidate.home_id FOR UPDATE;
        IF v_candidate.room_id IS NOT NULL THEN
            PERFORM 1 FROM public.rooms
            WHERE id = v_candidate.room_id AND home_id = v_candidate.home_id
            FOR UPDATE;
        END IF;
        PERFORM 1 FROM public.devices
        WHERE id = v_candidate.device_id AND home_id = v_candidate.home_id
        FOR UPDATE;

        SELECT o.*, r.delivery_id, r.attempt_count, c.expires_at
        INTO v_job
        FROM public.command_outbox o
        JOIN public.command_device_results r
          ON r.id = o.command_device_result_id
         AND r.command_id = o.command_id
         AND r.home_id = o.home_id
         AND r.device_id = o.device_id
        JOIN public.voice_commands c
          ON c.id = o.command_id AND c.home_id = o.home_id
        WHERE o.id = v_candidate.outbox_id
          AND o.state = 'pending'
          AND c.expires_at > pg_catalog.now()
          AND r.attempt_count < 5
        FOR UPDATE OF r, o;
        IF NOT FOUND THEN
            CONTINUE;
        END IF;

        UPDATE public.command_device_results
        SET attempt_count = attempt_count + 1,
            status = 'dispatched',
            updated_at = pg_catalog.now()
        WHERE id = v_job.command_device_result_id
          AND command_id = v_job.command_id
          AND home_id = v_job.home_id
          AND device_id = v_job.device_id
          AND attempt_count < 5;
        IF NOT FOUND THEN
            CONTINUE;
        END IF;

        UPDATE public.command_outbox
        SET state = 'processing', worker_id = p_worker_id,
            locked_at = pg_catalog.now(),
            lease_expires_at = pg_catalog.now() + (p_lease_seconds * interval '1 second'),
            last_attempt_at = pg_catalog.now(), updated_at = pg_catalog.now()
        WHERE id = v_job.id AND state = 'pending';
        IF NOT FOUND THEN
            RAISE EXCEPTION 'claim_lost';
        END IF;

        PERFORM public.refresh_voice_command_status(v_job.command_id, v_job.home_id);

        RETURN NEXT pg_catalog.jsonb_build_object(
            'outbox_id', v_job.id, 'command_id', v_job.command_id,
            'home_id', v_job.home_id, 'device_id', v_job.device_id,
            'result_id', v_job.command_device_result_id,
            'delivery_id', v_job.delivery_id,
            'attempt_count', v_job.attempt_count + 1,
            'expires_at', v_job.expires_at
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION public.refresh_voice_command_status(
    p_command_id UUID,
    p_home_id UUID
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_total INTEGER;
    v_acknowledged INTEGER;
    v_unknown INTEGER;
    v_active INTEGER;
    v_timed_out INTEGER;
    v_status TEXT;
BEGIN
    SELECT count(*), count(*) FILTER (WHERE r.status = 'acknowledged'),
           count(*) FILTER (WHERE r.status = 'unknown_outcome'),
           count(*) FILTER (WHERE o.state IN ('pending', 'processing')),
           count(*) FILTER (WHERE r.status = 'timed_out')
    INTO v_total, v_acknowledged, v_unknown, v_active, v_timed_out
    FROM public.command_device_results r
    JOIN public.command_outbox o
      ON o.command_device_result_id = r.id AND o.command_id = r.command_id
     AND o.home_id = r.home_id AND o.device_id = r.device_id
    WHERE r.command_id = p_command_id AND r.home_id = p_home_id;
    v_status := CASE
        WHEN v_unknown > 0 THEN 'unknown_outcome'
        WHEN v_total > 0 AND v_acknowledged = v_total THEN 'acknowledged'
        WHEN v_active > 0 THEN 'dispatched'
        WHEN v_acknowledged > 0 THEN 'partially_acknowledged'
        WHEN v_timed_out > 0 THEN 'timed_out'
        ELSE 'failed'
    END;
    UPDATE public.voice_commands
    SET status = v_status,
        terminal_at = CASE
            WHEN v_status = 'unknown_outcome' THEN NULL
            WHEN v_status IN ('acknowledged', 'partially_acknowledged', 'failed', 'timed_out')
                THEN coalesce(terminal_at, pg_catalog.now())
            ELSE NULL END,
        updated_at = pg_catalog.now()
    WHERE id = p_command_id AND home_id = p_home_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.recover_voice_command_outbox()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_candidate RECORD;
    v_job RECORD;
    v_count INTEGER := 0;
    v_retry BOOLEAN;
BEGIN
    -- Recheck each exact candidate after taking the same locks as claim/complete.
    FOR v_candidate IN
        SELECT o.id AS outbox_id, o.home_id, o.device_id, c.room_id
        FROM public.command_outbox o
        JOIN public.voice_commands c
          ON c.id = o.command_id AND c.home_id = o.home_id
        WHERE o.state = 'processing' AND o.lease_expires_at < pg_catalog.now()
        ORDER BY o.home_id, o.device_id, o.id
    LOOP
        PERFORM 1 FROM public.homes
        WHERE id = v_candidate.home_id FOR UPDATE;
        IF v_candidate.room_id IS NOT NULL THEN
            PERFORM 1 FROM public.rooms
            WHERE id = v_candidate.room_id AND home_id = v_candidate.home_id
            FOR UPDATE;
        END IF;
        PERFORM 1 FROM public.devices
        WHERE id = v_candidate.device_id AND home_id = v_candidate.home_id
        FOR UPDATE;

        SELECT o.*, r.status AS result_status, r.attempt_count, c.expires_at
        INTO v_job
        FROM public.command_outbox o
        JOIN public.command_device_results r
          ON r.id = o.command_device_result_id
         AND r.command_id = o.command_id
         AND r.home_id = o.home_id
         AND r.device_id = o.device_id
        JOIN public.voice_commands c
          ON c.id = o.command_id AND c.home_id = o.home_id
        WHERE o.id = v_candidate.outbox_id
          AND o.state = 'processing' AND o.lease_expires_at < pg_catalog.now()
        FOR UPDATE OF r, o;
        IF NOT FOUND THEN
            CONTINUE;
        END IF;

        v_retry := v_job.result_status <> 'failed'
                   AND v_job.attempt_count < 5 AND v_job.expires_at > pg_catalog.now();
        UPDATE public.command_outbox
        SET state = CASE WHEN v_retry THEN 'pending' ELSE 'failed' END,
            worker_id = NULL, locked_at = NULL, lease_expires_at = NULL,
            next_attempt_at = CASE WHEN v_retry THEN
                pg_catalog.now() + least(60, pg_catalog.power(2::numeric, v_job.attempt_count)::integer) * interval '1 second'
                ELSE next_attempt_at END,
            terminal_at = CASE WHEN v_retry THEN NULL ELSE pg_catalog.now() END,
            updated_at = pg_catalog.now()
        WHERE id = v_job.id AND state = 'processing';
        IF NOT FOUND THEN
            CONTINUE;
        END IF;

        -- A permanent failure is never rewritten as a timeout.
        IF NOT (v_job.result_status = 'failed' AND NOT v_retry) THEN
            UPDATE public.command_device_results
            SET status = 'timed_out', acknowledged = FALSE, acknowledged_at = NULL,
                terminal_at = CASE WHEN v_retry THEN NULL ELSE pg_catalog.now() END,
                updated_at = pg_catalog.now()
            WHERE id = v_job.command_device_result_id;
        END IF;
        PERFORM public.refresh_voice_command_status(v_job.command_id, v_job.home_id);
        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.complete_voice_command_outbox(
    p_outbox_id UUID, p_worker_id TEXT, p_delivery_id UUID, p_outcome TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_candidate RECORD;
    v_job RECORD;
    v_retry BOOLEAN;
BEGIN
    IF p_outcome NOT IN ('success', 'offline', 'permanent_failure', 'timeout', 'unknown') THEN
        RAISE EXCEPTION 'invalid_outcome' USING ERRCODE = '22023';
    END IF;

    SELECT o.home_id, o.device_id, c.room_id INTO v_candidate
    FROM public.command_outbox o
    JOIN public.voice_commands c ON c.id = o.command_id AND c.home_id = o.home_id
    WHERE o.id = p_outbox_id;
    IF NOT FOUND THEN RETURN FALSE; END IF;

    PERFORM 1 FROM public.homes WHERE id = v_candidate.home_id FOR UPDATE;
    IF v_candidate.room_id IS NOT NULL THEN
        PERFORM 1 FROM public.rooms
        WHERE id = v_candidate.room_id AND home_id = v_candidate.home_id FOR UPDATE;
    END IF;
    PERFORM 1 FROM public.devices
    WHERE id = v_candidate.device_id AND home_id = v_candidate.home_id FOR UPDATE;

    SELECT o.*, r.delivery_id, r.attempt_count, r.status AS result_status, c.expires_at
    INTO v_job
    FROM public.command_outbox o
    JOIN public.command_device_results r
      ON r.id = o.command_device_result_id
     AND r.command_id = o.command_id AND r.home_id = o.home_id AND r.device_id = o.device_id
    JOIN public.voice_commands c ON c.id = o.command_id AND c.home_id = o.home_id
    WHERE o.id = p_outbox_id AND o.worker_id = p_worker_id AND o.state = 'processing'
      AND r.delivery_id = p_delivery_id
      AND o.lease_expires_at > pg_catalog.now()
    FOR UPDATE OF r, o;
    IF NOT FOUND THEN
        IF EXISTS (
            SELECT 1 FROM public.command_outbox o
            WHERE o.id = p_outbox_id
              AND o.worker_id = p_worker_id
              AND o.state = 'processing'
              AND o.lease_expires_at <= pg_catalog.now()
        ) THEN
            RAISE EXCEPTION 'stale_lease' USING ERRCODE = '55000';
        END IF;
        RETURN FALSE;
    END IF;
    IF v_job.result_status = 'acknowledged' AND p_outcome = 'success' THEN RETURN TRUE; END IF;

    v_retry := p_outcome IN ('offline', 'timeout')
               AND v_job.attempt_count < 5 AND v_job.expires_at > pg_catalog.now();
    UPDATE public.command_outbox
    SET state = CASE WHEN p_outcome = 'success' THEN 'completed'
                     WHEN v_retry THEN 'pending' ELSE 'failed' END,
        worker_id = NULL, locked_at = NULL, lease_expires_at = NULL,
        next_attempt_at = CASE WHEN v_retry THEN
            pg_catalog.now() + least(60, pg_catalog.power(2::numeric, v_job.attempt_count)::integer) * interval '1 second'
            ELSE next_attempt_at END,
        terminal_at = CASE WHEN p_outcome IN ('success', 'permanent_failure')
                              OR (p_outcome IN ('offline', 'timeout') AND NOT v_retry)
                           THEN pg_catalog.now() ELSE NULL END,
        updated_at = pg_catalog.now()
    WHERE id = p_outbox_id AND worker_id = p_worker_id AND state = 'processing'
      AND lease_expires_at > pg_catalog.now();
    IF NOT FOUND THEN
        RAISE EXCEPTION 'stale_lease' USING ERRCODE = '55000';
    END IF;

    UPDATE public.command_device_results
    SET status = CASE WHEN p_outcome = 'success' THEN 'acknowledged'
                      WHEN p_outcome = 'offline' THEN 'device_offline'
                      WHEN p_outcome = 'timeout' THEN 'timed_out'
                      WHEN p_outcome = 'unknown' THEN 'unknown_outcome'
                      ELSE 'failed' END,
        acknowledged = (p_outcome = 'success'),
        acknowledged_at = CASE WHEN p_outcome = 'success' THEN pg_catalog.now() ELSE NULL END,
        terminal_at = CASE WHEN p_outcome = 'unknown' OR v_retry THEN NULL ELSE pg_catalog.now() END,
        updated_at = pg_catalog.now()
    WHERE id = v_job.command_device_result_id;
    PERFORM public.refresh_voice_command_status(v_job.command_id, v_job.home_id);
    RETURN TRUE;
END;
$$;

REVOKE ALL ON FUNCTION public.claim_voice_command_outbox(TEXT, INTEGER, INTEGER)
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.refresh_voice_command_status(UUID, UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.recover_voice_command_outbox() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.complete_voice_command_outbox(UUID, TEXT, UUID, TEXT)
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.claim_voice_command_outbox(TEXT, INTEGER, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.recover_voice_command_outbox() TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_voice_command_outbox(UUID, TEXT, UUID, TEXT) TO service_role;
