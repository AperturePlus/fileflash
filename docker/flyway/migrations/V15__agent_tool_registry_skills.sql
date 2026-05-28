UPDATE agent_skill
SET tool_whitelist_json = '[
    "drive.listFolder",
    "drive.countFiles",
    "drive.searchFiles",
    "drive.getFileInfo",
    "drive.listRecent",
    "drive.statsByCategory",
    "drive.findDuplicates",
    "drive.createFolder",
    "drive.moveFile",
    "drive.moveFolder",
    "drive.renameFile",
    "drive.renameFolder",
    "drive.deleteFile",
    "drive.deleteFolder"
]'::jsonb,
updated_at = CURRENT_TIMESTAMP
WHERE skill_key = 'builtin:organizeByType';
