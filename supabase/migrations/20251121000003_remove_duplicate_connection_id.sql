-- Remove duplicate connection_id column from push_subscriptions
-- We're standardizing on ext_connection_id which was in the original schema

-- First, ensure all existing data is migrated
UPDATE push_subscriptions 
SET ext_connection_id = connection_id 
WHERE ext_connection_id IS NULL AND connection_id IS NOT NULL;

-- Drop the index on connection_id
DROP INDEX IF EXISTS idx_push_subscriptions_connection_id;

-- Drop the duplicate column
ALTER TABLE push_subscriptions 
DROP COLUMN IF EXISTS connection_id;

-- Add a comment to clarify usage
COMMENT ON COLUMN push_subscriptions.ext_connection_id IS 'Foreign key to ext_connections table. Links this push subscription to a specific Google OAuth connection.';

