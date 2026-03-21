-- =========================
-- Domain: maintenance functions and views
-- =========================

CREATE OR REPLACE FUNCTION recalc_user_storage_used(p_user_id BIGINT)
RETURNS VOID AS $$
BEGIN
    IF p_user_id IS NULL THEN
        RETURN;
    END IF;

    UPDATE "user" u
    SET storage_used = COALESCE((
        SELECT SUM(f.file_size)
        FROM "file" f
        WHERE f.owner_id = p_user_id
          AND f.status = 'active'
    ), 0)
    WHERE u.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION recalc_storage_object_ref_count(p_object_id BIGINT)
RETURNS VOID AS $$
BEGIN
    IF p_object_id IS NULL THEN
        RETURN;
    END IF;

    UPDATE storage_object so
    SET ref_count = COALESCE((
        SELECT COUNT(*)
        FROM "file" f
        WHERE f.storage_object_id = p_object_id
          AND f.status = 'active'
    ), 0)
    WHERE so.object_id = p_object_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION recalc_folder_cached_size(p_folder_id BIGINT)
RETURNS VOID AS $$
DECLARE
    v_folder_id BIGINT := p_folder_id;
    v_parent_id BIGINT;
BEGIN
    WHILE v_folder_id IS NOT NULL LOOP
        UPDATE folder f
        SET cached_size =
            COALESCE((
                SELECT SUM(fi.file_size)
                FROM "file" fi
                WHERE fi.folder_id = f.folder_id
                  AND fi.status = 'active'
            ), 0)
            +
            COALESCE((
                SELECT SUM(ch.cached_size)
                FROM folder ch
                WHERE ch.parent_folder_id = f.folder_id
                  AND ch.status = 'active'
            ), 0)
        WHERE f.folder_id = v_folder_id;

        SELECT parent_folder_id INTO v_parent_id
        FROM folder
        WHERE folder_id = v_folder_id;

        v_folder_id := v_parent_id;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION rebuild_all_folder_cached_size()
RETURNS VOID AS $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        WITH RECURSIVE tree AS (
            SELECT folder_id, parent_folder_id, 0 AS depth
            FROM folder
            WHERE parent_folder_id IS NULL

            UNION ALL

            SELECT f.folder_id, f.parent_folder_id, t.depth + 1
            FROM folder f
            JOIN tree t ON f.parent_folder_id = t.folder_id
        )
        SELECT folder_id
        FROM tree
        ORDER BY depth DESC, folder_id DESC
    LOOP
        PERFORM recalc_folder_cached_size(r.folder_id);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION check_folder_parent_valid()
RETURNS TRIGGER AS $$
DECLARE
    v_parent_owner BIGINT;
    v_parent_status folder_status_enum;
    v_has_cycle BOOLEAN := FALSE;
BEGIN
    IF NEW.parent_folder_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT owner_id, status
      INTO v_parent_owner, v_parent_status
    FROM folder
    WHERE folder_id = NEW.parent_folder_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Parent folder % does not exist', NEW.parent_folder_id;
    END IF;

    IF v_parent_owner <> NEW.owner_id THEN
        RAISE EXCEPTION 'Parent folder owner must match folder owner';
    END IF;

    IF NEW.status = 'active' AND v_parent_status <> 'active' THEN
        RAISE EXCEPTION 'Active folder cannot be placed under a non-active parent folder';
    END IF;

    IF NEW.folder_id IS NOT NULL THEN
        IF NEW.parent_folder_id = NEW.folder_id THEN
            RAISE EXCEPTION 'Folder cannot be its own parent';
        END IF;

        WITH RECURSIVE descendants AS (
            SELECT folder_id
            FROM folder
            WHERE parent_folder_id = NEW.folder_id

            UNION ALL

            SELECT f.folder_id
            FROM folder f
            JOIN descendants d ON f.parent_folder_id = d.folder_id
        )
        SELECT EXISTS(
            SELECT 1
            FROM descendants
            WHERE folder_id = NEW.parent_folder_id
        )
        INTO v_has_cycle;

        IF v_has_cycle THEN
            RAISE EXCEPTION 'Folder cannot be moved into its own descendant';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_folder_validate ON folder;
CREATE TRIGGER trg_folder_validate
BEFORE INSERT OR UPDATE OF parent_folder_id, owner_id, status ON folder
FOR EACH ROW
EXECUTE FUNCTION check_folder_parent_valid();

CREATE OR REPLACE FUNCTION check_file_folder_valid()
RETURNS TRIGGER AS $$
DECLARE
    v_folder_owner BIGINT;
    v_folder_status folder_status_enum;
BEGIN
    SELECT owner_id, status
      INTO v_folder_owner, v_folder_status
    FROM folder
    WHERE folder_id = NEW.folder_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Folder % does not exist', NEW.folder_id;
    END IF;

    IF NEW.status = 'active' THEN
        IF v_folder_owner <> NEW.owner_id THEN
            RAISE EXCEPTION 'File owner must match folder owner';
        END IF;

        IF v_folder_status <> 'active' THEN
            RAISE EXCEPTION 'Active file cannot be placed under a non-active folder';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_file_validate ON "file";
CREATE TRIGGER trg_file_validate
BEFORE INSERT OR UPDATE OF folder_id, owner_id, status ON "file"
FOR EACH ROW
EXECUTE FUNCTION check_file_folder_valid();

CREATE OR REPLACE FUNCTION sync_file_derived_fields()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM recalc_storage_object_ref_count(NEW.storage_object_id);
        PERFORM recalc_user_storage_used(NEW.owner_id);
        PERFORM recalc_folder_cached_size(NEW.folder_id);
        RETURN NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        PERFORM recalc_storage_object_ref_count(OLD.storage_object_id);
        IF NEW.storage_object_id IS DISTINCT FROM OLD.storage_object_id THEN
            PERFORM recalc_storage_object_ref_count(NEW.storage_object_id);
        END IF;

        PERFORM recalc_user_storage_used(OLD.owner_id);
        IF NEW.owner_id IS DISTINCT FROM OLD.owner_id THEN
            PERFORM recalc_user_storage_used(NEW.owner_id);
        END IF;

        PERFORM recalc_folder_cached_size(OLD.folder_id);
        IF NEW.folder_id IS DISTINCT FROM OLD.folder_id THEN
            PERFORM recalc_folder_cached_size(NEW.folder_id);
        END IF;
        RETURN NULL;
    ELSE
        PERFORM recalc_storage_object_ref_count(OLD.storage_object_id);
        PERFORM recalc_user_storage_used(OLD.owner_id);
        PERFORM recalc_folder_cached_size(OLD.folder_id);
        RETURN NULL;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_file_sync_derived_fields ON "file";
CREATE TRIGGER trg_file_sync_derived_fields
AFTER INSERT OR UPDATE OR DELETE ON "file"
FOR EACH ROW
EXECUTE FUNCTION sync_file_derived_fields();

CREATE OR REPLACE FUNCTION sync_folder_cached_size()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM recalc_folder_cached_size(NEW.folder_id);
        PERFORM recalc_folder_cached_size(NEW.parent_folder_id);
        RETURN NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        PERFORM recalc_folder_cached_size(OLD.parent_folder_id);
        PERFORM recalc_folder_cached_size(NEW.folder_id);
        IF NEW.parent_folder_id IS DISTINCT FROM OLD.parent_folder_id THEN
            PERFORM recalc_folder_cached_size(NEW.parent_folder_id);
        END IF;
        RETURN NULL;
    ELSE
        PERFORM recalc_folder_cached_size(OLD.parent_folder_id);
        RETURN NULL;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_folder_sync_cached_size ON folder;
CREATE TRIGGER trg_folder_sync_cached_size
AFTER INSERT OR DELETE OR UPDATE OF parent_folder_id, status ON folder
FOR EACH ROW
EXECUTE FUNCTION sync_folder_cached_size();

UPDATE storage_object so
SET ref_count = x.ref_count
FROM (
    SELECT storage_object_id, COUNT(*) AS ref_count
    FROM "file"
    WHERE status = 'active'
    GROUP BY storage_object_id
) x
WHERE so.object_id = x.storage_object_id;

UPDATE storage_object so
SET ref_count = 0
WHERE NOT EXISTS (
    SELECT 1
    FROM "file" f
    WHERE f.storage_object_id = so.object_id
      AND f.status = 'active'
);

UPDATE "user" u
SET storage_used = x.total_size
FROM (
    SELECT owner_id AS user_id, COALESCE(SUM(file_size), 0) AS total_size
    FROM "file"
    WHERE status = 'active'
    GROUP BY owner_id
) x
WHERE u.user_id = x.user_id;

UPDATE "user" u
SET storage_used = 0
WHERE NOT EXISTS (
    SELECT 1
    FROM "file" f
    WHERE f.owner_id = u.user_id
      AND f.status = 'active'
);

SELECT rebuild_all_folder_cached_size();

DROP VIEW IF EXISTS v_shared_with_me;
DROP VIEW IF EXISTS v_user_permissions;
DROP VIEW IF EXISTS v_user_recycle_bin;
DROP VIEW IF EXISTS v_full_path;
DROP VIEW IF EXISTS v_file_folder_details;
DROP VIEW IF EXISTS v_user_storage_summary;
DROP VIEW IF EXISTS v_admin_share_overview;
DROP VIEW IF EXISTS v_user_dashboard;

CREATE VIEW v_file_folder_details AS
SELECT
    'file' AS item_type,
    f.file_id AS id,
    f.file_name AS name,
    f.file_size AS size,
    f.mime_type,
    f.folder_id AS parent_id,
    f.owner_id,
    u.username AS owner_name,
    f.created_at,
    f.updated_at
FROM "file" f
JOIN "user" u ON f.owner_id = u.user_id
JOIN storage_object so ON f.storage_object_id = so.object_id
WHERE f.status = 'active'
  AND so.upload_status = 'active'

UNION ALL

SELECT
    'folder' AS item_type,
    fo.folder_id AS id,
    fo.folder_name AS name,
    fo.cached_size AS size,
    'inode/directory' AS mime_type,
    fo.parent_folder_id AS parent_id,
    fo.owner_id,
    u.username AS owner_name,
    fo.created_at,
    fo.updated_at
FROM folder fo
JOIN "user" u ON fo.owner_id = u.user_id
WHERE fo.status = 'active';

CREATE VIEW v_user_permissions AS
SELECT
    acl.id AS acl_id,
    u.user_id,
    u.username AS user_name,
    COALESCE(f.file_id, fo.folder_id) AS item_id,
    COALESCE(f.file_name, fo.folder_name) AS item_name,
    CASE WHEN acl.file_id IS NOT NULL THEN 'file' ELSE 'folder' END AS item_type,
    acl.permission_role,
    acl.can_preview,
    acl.can_download,
    acl.can_save,
    acl.can_share,
    acl.expire_at,
    'direct'::TEXT AS grant_source
FROM acl
JOIN "user" u ON acl.user_id = u.user_id
LEFT JOIN "file" f ON acl.file_id = f.file_id AND f.status = 'active'
LEFT JOIN folder fo ON acl.folder_id = fo.folder_id AND fo.status = 'active'
WHERE acl.user_id IS NOT NULL
  AND (
      (acl.file_id IS NOT NULL AND f.file_id IS NOT NULL)
      OR
      (acl.folder_id IS NOT NULL AND fo.folder_id IS NOT NULL)
  )

UNION ALL

SELECT
    acl.id AS acl_id,
    u.user_id,
    u.username AS user_name,
    COALESCE(f.file_id, fo.folder_id) AS item_id,
    COALESCE(f.file_name, fo.folder_name) AS item_name,
    CASE WHEN acl.file_id IS NOT NULL THEN 'file' ELSE 'folder' END AS item_type,
    acl.permission_role,
    acl.can_preview,
    acl.can_download,
    acl.can_save,
    acl.can_share,
    acl.expire_at,
    'group'::TEXT AS grant_source
FROM acl
JOIN user_group_member ugm ON acl.group_id = ugm.group_id
JOIN "user" u ON ugm.user_id = u.user_id
LEFT JOIN "file" f ON acl.file_id = f.file_id AND f.status = 'active'
LEFT JOIN folder fo ON acl.folder_id = fo.folder_id AND fo.status = 'active'
WHERE acl.group_id IS NOT NULL
  AND (
      (acl.file_id IS NOT NULL AND f.file_id IS NOT NULL)
      OR
      (acl.folder_id IS NOT NULL AND fo.folder_id IS NOT NULL)
  );

CREATE VIEW v_user_storage_summary AS
SELECT
    user_id,
    username,
    status,
    storage_limit,
    storage_used,
    CASE
        WHEN storage_limit <= 0 THEN 0::NUMERIC(10,2)
        ELSE ROUND((storage_used::NUMERIC / storage_limit::NUMERIC) * 100, 2)
    END AS storage_used_pct
FROM "user";

CREATE VIEW v_shared_with_me AS
SELECT
    s.share_id,
    CASE WHEN s.file_id IS NOT NULL THEN 'file' ELSE 'folder' END AS item_type,
    COALESCE(f.file_id, fo.folder_id) AS item_id,
    COALESCE(f.file_name, fo.folder_name) AS item_name,
    owner.user_id AS shared_by_user_id,
    owner.username AS shared_by,
    sm.user_id AS shared_to_user_id,
    sm.status AS member_status,
    s.share_type,
    s.permission_role,
    s.allow_preview,
    s.allow_download,
    s.allow_save,
    s.allow_reshare,
    sm.target_folder_id,
    sm.accepted_at,
    s.expire_time,
    s.created_at AS shared_at
FROM share s
JOIN share_member sm ON s.share_id = sm.share_id
JOIN "user" owner ON s.user_id = owner.user_id
LEFT JOIN "file" f ON s.file_id = f.file_id AND f.status = 'active'
LEFT JOIN folder fo ON s.folder_id = fo.folder_id AND fo.status = 'active'
WHERE sm.user_id IS NOT NULL
  AND sm.status IN ('pending', 'accepted')
  AND s.status = 'active'
  AND (s.expire_time IS NULL OR s.expire_time > CURRENT_TIMESTAMP)
  AND (
      (s.file_id IS NOT NULL AND f.file_id IS NOT NULL)
      OR
      (s.folder_id IS NOT NULL AND fo.folder_id IS NOT NULL)
  )

UNION ALL

SELECT
    s.share_id,
    CASE WHEN s.file_id IS NOT NULL THEN 'file' ELSE 'folder' END AS item_type,
    COALESCE(f.file_id, fo.folder_id) AS item_id,
    COALESCE(f.file_name, fo.folder_name) AS item_name,
    owner.user_id AS shared_by_user_id,
    owner.username AS shared_by,
    ugm.user_id AS shared_to_user_id,
    sm.status AS member_status,
    s.share_type,
    s.permission_role,
    s.allow_preview,
    s.allow_download,
    s.allow_save,
    s.allow_reshare,
    sm.target_folder_id,
    sm.accepted_at,
    s.expire_time,
    s.created_at AS shared_at
FROM share s
JOIN share_member sm ON s.share_id = sm.share_id
JOIN user_group_member ugm ON sm.group_id = ugm.group_id
JOIN "user" owner ON s.user_id = owner.user_id
LEFT JOIN "file" f ON s.file_id = f.file_id AND f.status = 'active'
LEFT JOIN folder fo ON s.folder_id = fo.folder_id AND fo.status = 'active'
WHERE sm.group_id IS NOT NULL
  AND sm.status IN ('pending', 'accepted')
  AND s.status = 'active'
  AND (s.expire_time IS NULL OR s.expire_time > CURRENT_TIMESTAMP)
  AND (
      (s.file_id IS NOT NULL AND f.file_id IS NOT NULL)
      OR
      (s.folder_id IS NOT NULL AND fo.folder_id IS NOT NULL)
  );

CREATE VIEW v_full_path AS
WITH RECURSIVE folder_path AS (
    SELECT
        folder_id,
        owner_id,
        parent_folder_id,
        folder_name,
        CAST(folder_name AS VARCHAR(2048)) AS path
    FROM folder
    WHERE parent_folder_id IS NULL
      AND status = 'active'

    UNION ALL

    SELECT
        f.folder_id,
        f.owner_id,
        f.parent_folder_id,
        f.folder_name,
        fp.path || '/' || f.folder_name AS path
    FROM folder f
    JOIN folder_path fp
      ON f.parent_folder_id = fp.folder_id
     AND f.owner_id = fp.owner_id
    WHERE f.status = 'active'
)
SELECT
    folder_id AS id,
    owner_id,
    parent_folder_id,
    path
FROM folder_path;

CREATE VIEW v_user_recycle_bin AS
SELECT
    'file' AS item_type,
    f.file_id AS id,
    f.file_name AS name,
    f.file_size AS size,
    f.folder_id AS parent_id,
    f.owner_id,
    u.username AS owner_name,
    f.deleted_at
FROM "file" f
JOIN "user" u ON f.owner_id = u.user_id
WHERE f.status = 'deleted'
  AND f.deleted_at IS NOT NULL

UNION ALL

SELECT
    'folder' AS item_type,
    fo.folder_id AS id,
    fo.folder_name AS name,
    fo.cached_size AS size,
    fo.parent_folder_id AS parent_id,
    fo.owner_id,
    u.username AS owner_name,
    fo.deleted_at
FROM folder fo
JOIN "user" u ON fo.owner_id = u.user_id
WHERE fo.status = 'deleted'
  AND fo.deleted_at IS NOT NULL;

CREATE VIEW v_admin_share_overview AS
SELECT
    s.share_id,
    s.share_code,
    s.status,
    s.share_type,
    s.user_id AS created_by_user_id,
    u.username AS created_by,
    CASE WHEN s.file_id IS NOT NULL THEN 'file' ELSE 'folder' END AS item_type,
    COALESCE(f.file_id, fo.folder_id) AS item_id,
    COALESCE(f.file_name, fo.folder_name) AS item_name,
    s.permission_role,
    s.allow_preview,
    s.allow_download,
    s.allow_save,
    s.allow_reshare,
    s.require_login,
    s.password_hash IS NOT NULL AS has_password,
    s.expire_time,
    s.visit_count,
    s.download_count,
    s.created_at,
    s.updated_at
FROM share s
JOIN "user" u ON s.user_id = u.user_id
LEFT JOIN "file" f ON s.file_id = f.file_id
LEFT JOIN folder fo ON s.folder_id = fo.folder_id;

CREATE VIEW v_user_dashboard AS
SELECT
    u.user_id,
    u.username,
    u.email,
    u.status,
    u.storage_limit,
    u.storage_used,
    CASE
        WHEN u.storage_limit <= 0 THEN 0::NUMERIC(10,2)
        ELSE ROUND((u.storage_used::NUMERIC / u.storage_limit::NUMERIC) * 100, 2)
    END AS storage_used_pct,
    COALESCE(f.file_count, 0) AS active_file_count,
    COALESCE(fo.folder_count, 0) AS active_folder_count,
    COALESCE(s.active_share_count, 0) AS active_share_count,
    COALESCE(fv.favorite_count, 0) AS favorite_count,
    u.last_login_at,
    u.created_at
FROM "user" u
LEFT JOIN (
    SELECT owner_id, COUNT(*) AS file_count
    FROM "file"
    WHERE status = 'active'
    GROUP BY owner_id
) f ON u.user_id = f.owner_id
LEFT JOIN (
    SELECT owner_id, COUNT(*) AS folder_count
    FROM folder
    WHERE status = 'active'
    GROUP BY owner_id
) fo ON u.user_id = fo.owner_id
LEFT JOIN (
    SELECT user_id, COUNT(*) AS active_share_count
    FROM share
    WHERE status = 'active'
      AND (expire_time IS NULL OR expire_time > CURRENT_TIMESTAMP)
    GROUP BY user_id
) s ON u.user_id = s.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) AS favorite_count
    FROM favorite_item
    GROUP BY user_id
) fv ON u.user_id = fv.user_id;
