-- =========================
-- Domain: identity
-- Add avatar field for user profile
-- =========================

ALTER TABLE "user"
    ADD COLUMN IF NOT EXISTS avatar VARCHAR(512);

COMMENT ON COLUMN "user".avatar IS 'User avatar URL';
