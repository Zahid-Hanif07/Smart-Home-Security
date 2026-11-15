-- Phase 10.4B: owner-authenticated voice light command persistence.
-- Production acceptance is performed by create_voice_command(), which keeps
-- idempotency, the device snapshot, result rows, and outbox rows atomic.

ALTER TABLE public.devices
    ADD COLUMN IF NOT EXISTS room_id UUID NULL;

CREATE UNIQUE INDEX IF NOT EXISTS devices_id_home_uq
    ON public.devices(id, home_id);

CREATE TABLE IF NOT EXISTS public.rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES public.homes(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT rooms_name_not_blank CHECK (length(btrim(name)) > 0),
    CONSTRAINT rooms_id_home_uq UNIQUE (id, home_id)
);

CREATE OR REPLACE FUNCTION public.set_room_normalized_name()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    NEW.normalized_name := lower(
        regexp_replace(btrim(normalize(NEW.name, NFC)), '[[:space:]]+', ' ', 'g')
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS rooms_set_normalized_name ON public.rooms;
CREATE TRIGGER rooms_set_normalized_name
BEFORE INSERT OR UPDATE OF name ON public.rooms
FOR EACH ROW EXECUTE FUNCTION public.set_room_normalized_name();

REVOKE ALL ON FUNCTION public.set_room_normalized_name() FROM PUBLIC, anon, authenticated;

CREATE UNIQUE INDEX IF NOT EXISTS rooms_home_normalized_name_uq
    ON public.rooms(home_id, normalized_name);

ALTER TABLE public.devices
    ADD CONSTRAINT devices_room_home_fk
    FOREIGN KEY (room_id, home_id)
    REFERENCES public.rooms(id, home_id)
    ON DELETE RESTRICT;

CREATE TABLE IF NOT EXISTS public.device_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL,
    home_id UUID NOT NULL,
    capability TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'enabled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT device_capabilities_device_home_fk
        FOREIGN KEY (device_id, home_id)
        REFERENCES public.devices(id, home_id)
        ON DELETE RESTRICT,
    CONSTRAINT device_capabilities_uq UNIQUE (device_id, capability),
    CONSTRAINT device_capabilities_status_ck
        CHECK (status IN ('enabled', 'disabled'))
);

CREATE OR REPLACE FUNCTION public.validate_light_capability_room()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    IF NEW.capability = 'light_control' THEN
        PERFORM 1 FROM public.devices d
        WHERE d.id = NEW.device_id AND d.home_id = NEW.home_id
        FOR UPDATE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'light_control_device_missing' USING ERRCODE = '23503';
        END IF;
        PERFORM 1 FROM public.devices d
        WHERE d.id = NEW.device_id
          AND d.home_id = NEW.home_id
          AND d.room_id IS NOT NULL;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'light_control_requires_room' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.validate_device_light_room()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
BEGIN
    -- A device INSERT/UPDATE already holds the device row lock before this
    -- trigger runs; capability writes acquire that same lock explicitly.
    IF NEW.room_id IS NULL THEN
        PERFORM 1
        FROM public.device_capabilities c
        WHERE c.device_id = NEW.id
          AND c.home_id = NEW.home_id
          AND c.capability = 'light_control'
        ;
        IF FOUND THEN
            RAISE EXCEPTION 'light_control_requires_room' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS device_capabilities_require_room ON public.device_capabilities;
CREATE TRIGGER device_capabilities_require_room
BEFORE INSERT OR UPDATE OF device_id, home_id, capability, status
ON public.device_capabilities
FOR EACH ROW EXECUTE FUNCTION public.validate_light_capability_room();

DROP TRIGGER IF EXISTS devices_require_room_for_light ON public.devices;
CREATE TRIGGER devices_require_room_for_light
BEFORE INSERT OR UPDATE OF id, home_id, room_id
ON public.devices
FOR EACH ROW EXECUTE FUNCTION public.validate_device_light_room();

REVOKE ALL ON FUNCTION public.validate_light_capability_room() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.validate_device_light_room() FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS public.voice_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES public.homes(id) ON DELETE RESTRICT,
    owner_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    client_command_id UUID NOT NULL,
    command TEXT NOT NULL,
    target_type TEXT NOT NULL,
    room_id UUID NULL,
    request_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'accepted',
    expires_at TIMESTAMPTZ NOT NULL,
    terminal_at TIMESTAMPTZ NULL,
    resolved_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT voice_commands_id_home_uq UNIQUE (id, home_id),
    CONSTRAINT voice_commands_idempotency_uq UNIQUE (home_id, client_command_id),
    CONSTRAINT voice_commands_room_home_fk
        FOREIGN KEY (room_id, home_id)
        REFERENCES public.rooms(id, home_id)
        ON DELETE RESTRICT,
    CONSTRAINT voice_commands_command_ck CHECK (command IN (
        'light_on', 'light_off', 'all_lights_on', 'all_lights_off'
    )),
    CONSTRAINT voice_commands_target_ck CHECK (
        (target_type = 'room' AND room_id IS NOT NULL)
        OR (target_type = 'all_lights' AND room_id IS NULL)
    ),
    CONSTRAINT voice_commands_command_target_ck CHECK (
        (command IN ('light_on', 'light_off') AND target_type = 'room')
        OR
        (command IN ('all_lights_on', 'all_lights_off') AND target_type = 'all_lights')
    ),
    CONSTRAINT voice_commands_status_ck CHECK (status IN (
        'accepted', 'queued', 'dispatched', 'executing',
        'acknowledged', 'partially_acknowledged', 'failed',
        'timed_out', 'device_offline', 'unknown_outcome', 'expired'
    )),
    CONSTRAINT voice_commands_terminal_clock_ck CHECK (
        (status IN ('accepted', 'queued', 'dispatched', 'executing') AND terminal_at IS NULL)
        OR
         (status IN ('acknowledged', 'partially_acknowledged', 'failed',
                     'timed_out', 'device_offline', 'expired')
         AND terminal_at IS NOT NULL)
         OR (status = 'unknown_outcome' AND terminal_at IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS public.command_device_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    command_id UUID NOT NULL,
    home_id UUID NOT NULL,
    device_id UUID NOT NULL,
    delivery_id UUID NOT NULL DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'pending',
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    terminal_at TIMESTAMPTZ NULL,
    resolved_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT command_results_identity_uq
        UNIQUE (id, command_id, home_id, device_id),
    CONSTRAINT command_results_delivery_uq UNIQUE (delivery_id),
    CONSTRAINT command_results_command_home_fk
        FOREIGN KEY (command_id, home_id)
        REFERENCES public.voice_commands(id, home_id)
        ON DELETE RESTRICT,
    CONSTRAINT command_results_device_home_fk
        FOREIGN KEY (device_id, home_id)
        REFERENCES public.devices(id, home_id)
        ON DELETE RESTRICT,
    CONSTRAINT command_results_attempt_ck CHECK (attempt_count BETWEEN 0 AND 5),
    CONSTRAINT command_results_status_ck CHECK (status IN (
        'pending', 'dispatched', 'acknowledged', 'device_offline',
        'timed_out', 'failed', 'unknown_outcome', 'expired'
    )),
    CONSTRAINT command_results_ack_ck CHECK (
        (status = 'acknowledged' AND acknowledged AND acknowledged_at IS NOT NULL)
        OR (status <> 'acknowledged' AND NOT acknowledged AND acknowledged_at IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS public.command_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    command_device_result_id UUID NOT NULL,
    command_id UUID NOT NULL,
    home_id UUID NOT NULL,
    device_id UUID NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending',
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    worker_id TEXT NULL,
    locked_at TIMESTAMPTZ NULL,
    lease_expires_at TIMESTAMPTZ NULL,
    last_attempt_at TIMESTAMPTZ NULL,
    last_error_code TEXT NULL,
    terminal_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT command_outbox_result_fk
        FOREIGN KEY (command_device_result_id, command_id, home_id, device_id)
        REFERENCES public.command_device_results(id, command_id, home_id, device_id)
        ON DELETE RESTRICT,
    CONSTRAINT command_outbox_state_ck CHECK (
        state IN ('pending', 'processing', 'completed', 'failed', 'expired')
    ),
    CONSTRAINT command_outbox_lease_ck CHECK (
        (state = 'processing' AND worker_id IS NOT NULL AND locked_at IS NOT NULL
            AND lease_expires_at IS NOT NULL AND lease_expires_at > locked_at)
        OR (state <> 'processing' AND worker_id IS NULL AND locked_at IS NULL
            AND lease_expires_at IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS command_outbox_dispatch_idx
    ON public.command_outbox(state, next_attempt_at);
CREATE INDEX IF NOT EXISTS command_outbox_lease_idx
    ON public.command_outbox(state, lease_expires_at);
CREATE INDEX IF NOT EXISTS command_results_command_idx
    ON public.command_device_results(command_id);
CREATE INDEX IF NOT EXISTS command_results_device_idx
    ON public.command_device_results(home_id, device_id);

CREATE OR REPLACE FUNCTION public.create_voice_command(
    p_home_id UUID,
    p_owner_id UUID,
    p_client_command_id UUID,
    p_command TEXT,
    p_target_type TEXT,
    p_room_id UUID,
    p_request_hash TEXT,
    p_expires_at TIMESTAMPTZ
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
    v_home public.homes%ROWTYPE;
    v_existing public.voice_commands%ROWTYPE;
    v_command public.voice_commands%ROWTYPE;
    v_device RECORD;
    v_result_id UUID;
    v_count INTEGER := 0;
    v_now TIMESTAMPTZ;
    v_expires_at TIMESTAMPTZ;
BEGIN
    v_now := pg_catalog.now();
    SELECT * INTO v_home FROM public.homes
    WHERE id = p_home_id AND owner_id = p_owner_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'home_not_authorized' USING ERRCODE = '42501'; END IF;

    IF p_request_hash IS NULL OR pg_catalog.btrim(p_request_hash) = '' THEN
        RAISE EXCEPTION 'invalid_request_hash' USING ERRCODE = '22023';
    END IF;

    SELECT * INTO v_existing FROM public.voice_commands
    WHERE home_id = p_home_id AND client_command_id = p_client_command_id;
    IF FOUND THEN
        IF v_existing.request_hash <> p_request_hash THEN
            RAISE EXCEPTION 'idempotency_conflict' USING ERRCODE = '23505';
        END IF;
        SELECT count(*) INTO v_count
        FROM public.command_device_results
        WHERE command_id = v_existing.id;
        RETURN jsonb_build_object('command', to_jsonb(v_existing),
                                  'existing', true, 'device_count', v_count);
    END IF;

    -- Five minutes is the server-controlled maximum command lifetime. The API
    -- supplies this value from server time; this RPC rejects stale/future values.
    IF p_expires_at IS NULL
       OR p_expires_at <= v_now
       OR p_expires_at > v_now + interval '5 minutes' THEN
        RAISE EXCEPTION 'invalid_command_expiry' USING ERRCODE = '22023';
    END IF;
    v_expires_at := v_now + interval '5 minutes';

    IF (p_command IN ('light_on', 'light_off') AND p_target_type <> 'room')
       OR (p_command IN ('all_lights_on', 'all_lights_off') AND p_target_type <> 'all_lights') THEN
        RAISE EXCEPTION 'invalid_target' USING ERRCODE = '22023';
    ELSIF p_target_type = 'room' THEN
        PERFORM 1 FROM public.rooms WHERE id = p_room_id AND home_id = p_home_id FOR UPDATE;
        IF NOT FOUND THEN RAISE EXCEPTION 'invalid_room' USING ERRCODE = '23503'; END IF;
    ELSIF p_target_type <> 'all_lights' OR p_room_id IS NOT NULL THEN
        RAISE EXCEPTION 'invalid_target' USING ERRCODE = '22023';
    END IF;

    INSERT INTO public.voice_commands(
        home_id, owner_id, client_command_id, command, target_type, room_id,
        request_hash, expires_at
    ) VALUES (
        p_home_id, p_owner_id, p_client_command_id, p_command, p_target_type,
        p_room_id, p_request_hash, v_expires_at
    ) RETURNING * INTO v_command;

    -- Capability writers lock the device row before changing capability state.
    -- Lock the full target set first, then run the eligibility query in a new
    -- statement snapshot so the frozen set reflects committed capability data.
    PERFORM d.id
    FROM public.devices d
    WHERE d.home_id = p_home_id
      AND (p_target_type = 'all_lights' OR d.room_id = p_room_id)
    ORDER BY d.id
    FOR UPDATE;

    FOR v_device IN
        SELECT d.id
        FROM public.devices d
        JOIN public.device_capabilities c ON c.device_id = d.id AND c.home_id = d.home_id
        WHERE d.home_id = p_home_id
          AND c.capability = 'light_control'
          AND c.status = 'enabled'
          AND (p_target_type = 'all_lights' OR d.room_id = p_room_id)
        ORDER BY d.id
    LOOP
        INSERT INTO public.command_device_results(command_id, home_id, device_id)
        VALUES (v_command.id, p_home_id, v_device.id)
        RETURNING id INTO v_result_id;
        INSERT INTO public.command_outbox(
            command_device_result_id, command_id, home_id, device_id
        ) VALUES (v_result_id, v_command.id, p_home_id, v_device.id);
        v_count := v_count + 1;
    END LOOP;

    IF v_count = 0 THEN
        RAISE EXCEPTION 'no_eligible_devices' USING ERRCODE = '23514';
    END IF;

    RETURN jsonb_build_object('command', to_jsonb(v_command), 'existing', false,
                              'device_count', v_count);
END;
$$;

REVOKE ALL ON FUNCTION public.create_voice_command(UUID, UUID, UUID, TEXT, TEXT, UUID, TEXT, TIMESTAMPTZ)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_voice_command(UUID, UUID, UUID, TEXT, TEXT, UUID, TEXT, TIMESTAMPTZ)
TO service_role;

ALTER TABLE public.rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.device_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.voice_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.command_device_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.command_outbox ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.device_capabilities,
    public.voice_commands,
    public.command_device_results,
    public.command_outbox
FROM anon, authenticated;

REVOKE ALL ON public.rooms FROM anon, authenticated;
GRANT SELECT ON public.rooms TO authenticated;
GRANT SELECT ON public.homes TO authenticated;
GRANT SELECT ON public.voice_commands TO authenticated;
GRANT SELECT ON public.command_device_results TO authenticated;
GRANT SELECT ON public.device_capabilities TO authenticated;

CREATE POLICY rooms_owner_select ON public.rooms
FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.homes h
            WHERE h.id = rooms.home_id AND h.owner_id = auth.uid())
);

CREATE POLICY capabilities_owner_select ON public.device_capabilities
FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.homes h
            WHERE h.id = device_capabilities.home_id AND h.owner_id = auth.uid())
);

CREATE POLICY commands_owner_select ON public.voice_commands
FOR SELECT TO authenticated USING (owner_id = auth.uid());

CREATE POLICY command_results_owner_select ON public.command_device_results
FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.voice_commands c
            WHERE c.id = command_device_results.command_id
              AND c.home_id = command_device_results.home_id
              AND c.owner_id = auth.uid())
);
