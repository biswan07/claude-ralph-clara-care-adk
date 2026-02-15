-- Add webhook_response column to warranty_claims table
-- This column stores the final JSON response sent to the webhook/user,
-- including actions taken and the full email body.

ALTER TABLE public.warranty_claims 
ADD COLUMN IF NOT EXISTS webhook_response JSONB;

-- Comment on column
COMMENT ON COLUMN public.warranty_claims.webhook_response IS 'Stores the final JSON response sent to the webhook, including actions and email body';
