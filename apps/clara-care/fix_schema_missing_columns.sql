-- Fix for missing columns in claim_status_history and warranty_claims

-- 1. Ensure warranty_claims has all needed columns
ALTER TABLE public.warranty_claims 
ADD COLUMN IF NOT EXISTS attempted_emails TEXT,
ADD COLUMN IF NOT EXISTS judge_reasoning TEXT,
ADD COLUMN IF NOT EXISTS pending_reason TEXT,
ADD COLUMN IF NOT EXISTS support_email_used TEXT,
ADD COLUMN IF NOT EXISTS confidence_score FLOAT;


-- 2. Add missing columns to claim_status_history to match the Python code
ALTER TABLE public.claim_status_history
ADD COLUMN IF NOT EXISTS support_email_used TEXT,
ADD COLUMN IF NOT EXISTS confidence_score FLOAT,
ADD COLUMN IF NOT EXISTS judge_reasoning TEXT,
ADD COLUMN IF NOT EXISTS attempted_emails TEXT,
ADD COLUMN IF NOT EXISTS pending_reason TEXT,
ADD COLUMN IF NOT EXISTS created_by TEXT;
