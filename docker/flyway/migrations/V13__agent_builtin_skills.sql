INSERT INTO agent_skill (
    skill_key,
    name,
    description,
    triggers_text,
    tool_whitelist_json,
    plan_template_json,
    inputs_schema_json,
    outputs_schema_json,
    visibility,
    owner_user_id
)
VALUES (
    'builtin:organizeByType',
    'Organize By Type',
    'Analyze the current folder metadata and propose folder creation, moves, and safe renames to organize files by type.',
    'organize files, organize by type, classify files, 整理文件, 文件分类',
    '[
        "drive.listFolder",
        "drive.createFolder",
        "drive.moveFile",
        "drive.moveFolder",
        "drive.renameFile",
        "drive.renameFolder",
        "drive.deleteFile",
        "drive.deleteFolder"
    ]'::jsonb,
    '{
        "strategy": "Group direct children by broad file type unless the user asks for a different organization rule.",
        "scope": "selected items when present; otherwise current folder direct children only",
        "deletePolicy": "delete actions are high risk and require explicit user confirmation"
    }'::jsonb,
    '{"type":"object"}'::jsonb,
    '{"type":"object"}'::jsonb,
    'global',
    NULL
)
ON CONFLICT (skill_key) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    triggers_text = EXCLUDED.triggers_text,
    tool_whitelist_json = EXCLUDED.tool_whitelist_json,
    plan_template_json = EXCLUDED.plan_template_json,
    inputs_schema_json = EXCLUDED.inputs_schema_json,
    outputs_schema_json = EXCLUDED.outputs_schema_json,
    visibility = EXCLUDED.visibility,
    owner_user_id = EXCLUDED.owner_user_id;
