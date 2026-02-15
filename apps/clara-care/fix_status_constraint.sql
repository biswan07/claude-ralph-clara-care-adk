-- Fix warranty_claims status constraint and missing columns

-- 1. Drop the existing check constraint on status
ALTER TABLE public.warranty_claims 
DROP CONSTRAINT IF EXISTS warranty_claims_status_check;

-- 2. Add the new check constraint with all allowed values
ALTER TABLE public.warranty_claims 
ADD CONSTRAINT warranty_claims_status_check 
CHECK (status IN ('pending', 'submitted', 'requires_review', 'failed', 'approved', 'rejected', 'new', 'in_progress'));

-- 3. Ensure all columns required by the agent are present (idempotent)
ALTER TABLE public.warranty_claims 
ADD COLUMN IF NOT EXISTS confidence_score FLOAT,
ADD COLUMN IF NOT EXISTS support_email_used TEXT,
ADD COLUMN IF NOT EXISTS judge_reasoning TEXT,
ADD COLUMN IF NOT EXISTS pending_reason TEXT,
ADD COLUMN IF NOT EXISTS attempted_emails TEXT;

-- 4. Create support_contacts table if it doesn't exist (for future use)
CREATE TABLE IF NOT EXISTS public.support_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name TEXT NOT NULL,
    support_email TEXT,
    support_phone TEXT,
    support_url TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    source TEXT,
    product_category TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for support_contacts
CREATE INDEX IF NOT EXISTS idx_support_contacts_brand_name ON public.support_contacts(brand_name);

-- RLS for support_contacts
ALTER TABLE public.support_contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access" ON public.support_contacts FOR SELECT USING (true);
CREATE POLICY "Allow authenticated insert" ON public.support_contacts FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Allow authenticated update" ON public.support_contacts FOR UPDATE USING (auth.role() = 'authenticated');

-- 5. Create claim_status_history table (audit trail)
CREATE TABLE IF NOT EXISTS public.claim_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id TEXT NOT NULL,
    status TEXT NOT NULL,
    change_reason TEXT,
    changed_by UUID DEFAULT auth.uid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for history
CREATE INDEX IF NOT EXISTS idx_claim_status_history_claim_id ON public.claim_status_history(claim_id);

-- RLS for history
ALTER TABLE public.claim_status_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read access" ON public.claim_status_history FOR SELECT USING (true);
CREATE POLICY "Allow authenticated insert" ON public.claim_status_history FOR INSERT WITH CHECK (auth.role() = 'authenticated');
