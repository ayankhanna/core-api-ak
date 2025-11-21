-- Add missing columns to push_subscriptions table
-- These fields are required by the watch manager and webhook handlers

-- Add provider column (gmail or calendar)
ALTER TABLE push_subscriptions 
ADD COLUMN IF NOT EXISTS provider TEXT;

-- Add connection_id to link back to ext_connections
ALTER TABLE push_subscriptions 
ADD COLUMN IF NOT EXISTS connection_id UUID REFERENCES ext_connections(id) ON DELETE CASCADE;

-- Add history_id for Gmail incremental sync
ALTER TABLE push_subscriptions 
ADD COLUMN IF NOT EXISTS history_id TEXT;

-- Add sync_token for Calendar incremental sync
ALTER TABLE push_subscriptions 
ADD COLUMN IF NOT EXISTS sync_token TEXT;

-- Add notification tracking fields
ALTER TABLE push_subscriptions 
ADD COLUMN IF NOT EXISTS notification_count INTEGER DEFAULT 0;

ALTER TABLE push_subscriptions 
ADD COLUMN IF NOT EXISTS last_notification_at TIMESTAMPTZ;

-- Add metadata for storing additional watch info
ALTER TABLE push_subscriptions 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Make resource_id nullable (Gmail doesn't use it)
ALTER TABLE push_subscriptions 
ALTER COLUMN resource_id DROP NOT NULL;

-- Make resource_type nullable (we use 'provider' instead)
ALTER TABLE push_subscriptions 
ALTER COLUMN resource_type DROP NOT NULL;

-- Add index for provider lookups
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_provider 
ON push_subscriptions(provider);

-- Add index for connection_id
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_connection_id 
ON push_subscriptions(connection_id);

-- Add comment explaining the schema
COMMENT ON TABLE push_subscriptions IS 'Tracks Google push notification subscriptions (watches) for Gmail and Calendar. Watches expire after 7 days and must be renewed.';

