-- =============================================================================
-- SMART HOME SECURITY & VOICE ASSISTANT - SUPABASE POSTGRESQL DATABASE SCHEMA
-- Step 6 Backend Foundation
-- =============================================================================

-- Enable pgcrypto for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. PROFILES TABLE (Associated with Supabase Auth auth.users)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    image_url TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Automatic trigger to create profile record when a new user signs up in Supabase Auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, name, email)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'name', NEW.email),
        NEW.email
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger definition
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- -----------------------------------------------------------------------------
-- 2. HOMES TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.homes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    address TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast owner queries
CREATE INDEX IF NOT EXISTS idx_homes_owner ON public.homes(owner_id);

-- -----------------------------------------------------------------------------
-- 3. HOME MEMBERS TABLE (Authorized people / family members)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.home_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
    user_id UUID NULL REFERENCES public.profiles(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    relation TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_home_members_home ON public.home_members(home_id);
CREATE INDEX IF NOT EXISTS idx_home_members_user ON public.home_members(user_id);

-- -----------------------------------------------------------------------------
-- 4. FACE RECORDS TABLE (Metadata for synchronization & remote storage)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.face_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id UUID NOT NULL REFERENCES public.home_members(id) ON DELETE CASCADE,
    image_path TEXT NULL,
    embedding JSONB NULL,
    sample_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_face_records_member ON public.face_records(member_id);

-- -----------------------------------------------------------------------------
-- 5. DEVICES TABLE (Webcam controllers, ESP32, Arduino, Door locks)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
    device_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_identifier TEXT UNIQUE NULL,
    status TEXT DEFAULT 'offline',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_devices_home ON public.devices(home_id);

-- -----------------------------------------------------------------------------
-- 6. SECURITY LOGS TABLE (Motion, detection, and recognition events)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.security_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
    device_id UUID NULL REFERENCES public.devices(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    description TEXT NULL,
    person_name TEXT NULL,
    is_authorized BOOLEAN NULL,
    image_path TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_logs_home ON public.security_logs(home_id);
CREATE INDEX IF NOT EXISTS idx_security_logs_event_type ON public.security_logs(event_type);

-- -----------------------------------------------------------------------------
-- 7. ALERTS TABLE (Security notifications and unauthorized detections)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES public.homes(id) ON DELETE CASCADE,
    security_log_id UUID NULL REFERENCES public.security_logs(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    image_path TEXT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_home ON public.alerts(home_id);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read ON public.alerts(is_read);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.homes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.home_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.face_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.security_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

-- Profiles Policies
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

-- Homes Policies
CREATE POLICY "Owners can view own homes"
    ON public.homes FOR SELECT
    USING (auth.uid() = owner_id);

CREATE POLICY "Owners can insert own homes"
    ON public.homes FOR INSERT
    WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Owners can update own homes"
    ON public.homes FOR UPDATE
    USING (auth.uid() = owner_id);

CREATE POLICY "Owners can delete own homes"
    ON public.homes FOR DELETE
    USING (auth.uid() = owner_id);

-- Home Members Policies
CREATE POLICY "Owners can view home members"
    ON public.home_members FOR SELECT
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can insert home members"
    ON public.home_members FOR INSERT
    WITH CHECK (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can update home members"
    ON public.home_members FOR UPDATE
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can delete home members"
    ON public.home_members FOR DELETE
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

-- Face Records Policies
CREATE POLICY "Owners can view face records"
    ON public.face_records FOR SELECT
    USING (
        member_id IN (
            SELECT hm.id FROM public.home_members hm
            JOIN public.homes h ON hm.home_id = h.id
            WHERE h.owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can insert face records"
    ON public.face_records FOR INSERT
    WITH CHECK (
        member_id IN (
            SELECT hm.id FROM public.home_members hm
            JOIN public.homes h ON hm.home_id = h.id
            WHERE h.owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can delete face records"
    ON public.face_records FOR DELETE
    USING (
        member_id IN (
            SELECT hm.id FROM public.home_members hm
            JOIN public.homes h ON hm.home_id = h.id
            WHERE h.owner_id = auth.uid()
        )
    );

-- Devices Policies
CREATE POLICY "Owners can view devices"
    ON public.devices FOR SELECT
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can manage devices"
    ON public.devices FOR ALL
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

-- Security Logs Policies
CREATE POLICY "Owners can view security logs"
    ON public.security_logs FOR SELECT
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can insert security logs"
    ON public.security_logs FOR INSERT
    WITH CHECK (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

-- Alerts Policies
CREATE POLICY "Owners can view alerts"
    ON public.alerts FOR SELECT
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can update alerts"
    ON public.alerts FOR UPDATE
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Owners can delete alerts"
    ON public.alerts FOR DELETE
    USING (
        home_id IN (
            SELECT id FROM public.homes WHERE owner_id = auth.uid()
        )
    );

-- =============================================================================
-- SUPABASE STORAGE BUCKET FOUNDATION
-- =============================================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('security-images', 'security-images', false)
ON CONFLICT (id) DO NOTHING;

-- RLS for Storage Bucket (security-images): Home ownership path restriction
CREATE POLICY "Users can access own home security images"
    ON storage.objects FOR ALL
    TO authenticated
    USING (
        bucket_id = 'security-images' AND
        (storage.foldername(name))[1] IN (
            SELECT id::text FROM public.homes WHERE owner_id = auth.uid()
        )
    );


-- =============================================================================
-- SUPABASE REALTIME PUBLICATION FOUNDATION
-- =============================================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.alerts;
ALTER PUBLICATION supabase_realtime ADD TABLE public.security_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.devices;
