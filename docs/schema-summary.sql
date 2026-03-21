-- PostgreSQL schema entrypoint (domain-splitted)
-- Usage (from repository root):
--   psql -U <user> -d <db> -f docs/schema-postgres.sql

\ir sql/postgres/00_base.sql
\ir sql/postgres/10_identity.sql
\ir sql/postgres/20_storage.sql
\ir sql/postgres/30_access_share.sql
\ir sql/postgres/40_audit_security.sql
\ir sql/postgres/50_maintenance_views.sql
\ir sql/postgres/90_comments.sql
