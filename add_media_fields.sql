-- Manual migration: Add media fields to bot_settings table
-- Execute this SQL script on your PostgreSQL database

-- Add welcome_message_media column
ALTER TABLE bot_settings
ADD COLUMN IF NOT EXISTS welcome_message_media VARCHAR(200) NULL;

COMMENT ON COLUMN bot_settings.welcome_message_media IS 'File ID медиа для приветственного сообщения';

-- Add help_message_media column
ALTER TABLE bot_settings
ADD COLUMN IF NOT EXISTS help_message_media VARCHAR(200) NULL;

COMMENT ON COLUMN bot_settings.help_message_media IS 'File ID медиа для сообщения помощи';

-- Add large_order_message_media column
ALTER TABLE bot_settings
ADD COLUMN IF NOT EXISTS large_order_message_media VARCHAR(200) NULL;

COMMENT ON COLUMN bot_settings.large_order_message_media IS 'File ID медиа для сообщения о большом заказе';

-- Verify the columns were added
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'bot_settings'
AND column_name LIKE '%_media';
