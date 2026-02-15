-- Create manual_review_requests table for storing drafts that need human review
CREATE TABLE IF NOT EXISTS public.manual_review_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id TEXT NOT NULL REFERENCES public.warranty_claims(claim_id) ON DELETE CASCADE,
    receipt_image_url TEXT,
    email_body_text TEXT,
    email_body_html TEXT,
    support_email TEXT,
    confidence_score FLOAT,
    assigned_to TEXT,
    reviewed_on TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'pending' -- pending, processed
);

-- Index for searching
CREATE INDEX IF NOT EXISTS idx_manual_review_requests_claim_id ON public.manual_review_requests(claim_id);
CREATE INDEX IF NOT EXISTS idx_manual_review_requests_status ON public.manual_review_requests(status);
CREATE INDEX IF NOT EXISTS idx_manual_review_requests_assigned_to ON public.manual_review_requests(assigned_to);

-- RLS Policies
ALTER TABLE public.manual_review_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated full access" ON public.manual_review_requests
    FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
