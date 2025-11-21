-- Add last_synced column to ext_connections table
-- This tracks when each connection last performed a sync operation

ALTER TABLE ext_connections 
ADD COLUMN IF NOT EXISTS last_synced TIMESTAMPTZ;

-- Create index for faster queries on last_synced
CREATE INDEX IF NOT EXISTS idx_ext_connections_last_synced 
ON ext_connections(last_synced);

