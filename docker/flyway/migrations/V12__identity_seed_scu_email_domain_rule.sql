-- =========================
-- Domain: identity
-- Seed default registration email domain rule
-- =========================

INSERT INTO registration_email_domain_rule (
    name,
    pattern,
    enabled
)
VALUES (
    'allow_scu_edu_cn',
    '(?:[a-z0-9-]+\.)*scu\.edu\.cn',
    TRUE
)
ON CONFLICT DO NOTHING;
