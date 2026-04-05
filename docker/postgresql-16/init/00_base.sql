-- =========================
-- Base: extensions, enum types, common trigger functions
-- =========================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'upload_status_enum') THEN
        CREATE TYPE upload_status_enum AS ENUM ('uploading', 'active', 'deleted', 'failed');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'folder_status_enum') THEN
        CREATE TYPE folder_status_enum AS ENUM ('active', 'deleted');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'file_status_enum') THEN
        CREATE TYPE file_status_enum AS ENUM ('active', 'deleted');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'upload_mode_enum') THEN
        CREATE TYPE upload_mode_enum AS ENUM ('single', 'multipart');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'upload_task_status_enum') THEN
        CREATE TYPE upload_task_status_enum AS ENUM ('init', 'uploading', 'completed', 'aborted', 'failed');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'upload_part_status_enum') THEN
        CREATE TYPE upload_part_status_enum AS ENUM ('pending', 'uploaded', 'failed');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_status_enum') THEN
        CREATE TYPE user_status_enum AS ENUM ('pending_verification', 'active', 'locked', 'disabled');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_enum') THEN
        CREATE TYPE user_role_enum AS ENUM ('USER', 'ADMIN');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ui_language_enum') THEN
        CREATE TYPE ui_language_enum AS ENUM ('zh-CN', 'en-US');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'folder_type_enum') THEN
        CREATE TYPE folder_type_enum AS ENUM ('normal', 'root', 'system');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'share_status_enum') THEN
        CREATE TYPE share_status_enum AS ENUM ('active', 'expired', 'revoked', 'deleted');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'share_member_status_enum') THEN
        CREATE TYPE share_member_status_enum AS ENUM ('pending', 'accepted', 'rejected', 'revoked');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'favorite_item_type_enum') THEN
        CREATE TYPE favorite_item_type_enum AS ENUM ('file', 'folder');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'view_mode_enum') THEN
        CREATE TYPE view_mode_enum AS ENUM ('list', 'grid');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sort_by_enum') THEN
        CREATE TYPE sort_by_enum AS ENUM ('name', 'size', 'created_at', 'updated_at', 'last_accessed_at');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sort_direction_enum') THEN
        CREATE TYPE sort_direction_enum AS ENUM ('asc', 'desc');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'preview_status_enum') THEN
        CREATE TYPE preview_status_enum AS ENUM ('pending', 'ready', 'failed');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'scan_result_enum') THEN
        CREATE TYPE scan_result_enum AS ENUM ('pending', 'clean', 'infected', 'blocked', 'failed');
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
