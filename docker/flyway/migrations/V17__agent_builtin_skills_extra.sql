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
VALUES
(
    'builtin:dedupScan',
    'Dedup Scan',
    'Find duplicate files by content hash or name+size and propose deletion of duplicates.',
    'duplicate files, dedup, find duplicates, 重复文件, 去重',
    '["drive.listFolder","drive.getFileInfo","drive.findDuplicates","drive.deleteFile"]'::jsonb,
    '{"strategy":"Group duplicates by content hash; propose keeping the oldest and deleting the rest. Deletions are high risk and require explicit confirmation."}'::jsonb,
    '{"type":"object","required":["sourceFolderId"],"properties":{"sourceFolderId":{"type":"string"},"by":{"type":"string","enum":["hash","nameSize"],"default":"hash"}}}'::jsonb,
    '{"type":"object"}'::jsonb,
    'global',
    NULL
),
(
    'builtin:listAndSummarize',
    'List And Summarize',
    'List the contents of a folder and produce a statistical summary by category.',
    'list files, summarize, folder summary, statistics, 列出文件, 统计摘要',
    '["drive.listFolder","drive.countFiles","drive.getFileInfo","drive.statsByCategory"]'::jsonb,
    '{"strategy":"List direct children, then compute counts and sizes by category. Read-only; no writes."}'::jsonb,
    '{"type":"object","required":["sourceFolderId"],"properties":{"sourceFolderId":{"type":"string"}}}'::jsonb,
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
