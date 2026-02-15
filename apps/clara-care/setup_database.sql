-- Create support_contacts table if it doesn't exist
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

-- Add indexes for faster search
CREATE INDEX IF NOT EXISTS idx_support_contacts_brand_name ON public.support_contacts(brand_name);

-- Grant access (adjust based on your security policies, these are permissive for dev)
ALTER TABLE public.support_contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access" ON public.support_contacts
    FOR SELECT USING (true);

CREATE POLICY "Allow authenticated insert" ON public.support_contacts
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Allow authenticated update" ON public.support_contacts
    FOR UPDATE USING (auth.role() = 'authenticated');

-- Fix missing columns in warranty_claims table
ALTER TABLE public.warranty_claims 
ADD COLUMN IF NOT EXISTS judge_reasoning TEXT,
ADD COLUMN IF NOT EXISTS pending_reason TEXT,
ADD COLUMN IF NOT EXISTS attempted_emails TEXT; -- Using TEXT to store JSON string output from agent
