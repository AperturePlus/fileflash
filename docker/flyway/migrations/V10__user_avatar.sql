-- Align "user" with ORM (tables_identity.User.avatar)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS avatar VARCHAR(512) NULL;
