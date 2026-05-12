import type { AppLanguage } from '../types/user';

export type LocaleKey =
  | 'common.language.zhCN'
  | 'common.language.enUS'
  | 'header.expandSidebar'
  | 'header.collapseSidebar'
  | 'header.brandSubtitle'
  | 'header.searchPlaceholder'
  | 'header.toggleTheme'
  | 'header.hidePreviewPanel'
  | 'header.showPreviewPanel'
  | 'header.userMenu'
  | 'header.menu.profile'
  | 'header.menu.settings'
  | 'header.menu.dashboard'
  | 'header.menu.logout'
  | 'header.menu.admin'
  | 'header.menu.defaultUserName'
  | 'header.menu.defaultEmail'
  | 'sidebar.myFiles'
  | 'sidebar.shared'
  | 'sidebar.recycleBin'
  | 'sidebar.workspaceTree'
  | 'sidebar.storage'
  | 'sidebar.skills'
  | 'sidebar.agent'
  | 'agent.pageTitle'
  | 'agent.pageDescription'
  | 'agent.nav.workspace'
  | 'agent.nav.skills'
  | 'agent.workspace.controls'
  | 'agent.workspace.advancedSettings'
  | 'agent.workspace.planPreview'
  | 'agent.workspace.executionResult'
  | 'agent.workspace.emptyPlan'
  | 'agent.workspace.executing'
  | 'agent.workspace.emptyExecution'
  | 'agent.fields.task'
  | 'agent.fields.taskPlaceholder'
  | 'agent.fields.executionPolicy'
  | 'agent.fields.allowFileContent'
  | 'agent.fields.maxReadBytes'
  | 'agent.fields.allowedMimeTypes'
  | 'agent.fields.maxSteps'
  | 'agent.fields.budgetTokens'
  | 'agent.fields.planHash'
  | 'agent.fields.chosenSkill'
  | 'agent.actions.plan'
  | 'agent.actions.reset'
  | 'agent.actions.execute'
  | 'agent.actions.cancel'
  | 'agent.actions.cancelled'
  | 'agent.metrics.planStatus'
  | 'agent.metrics.executeStatus'
  | 'agent.metrics.actions'
  | 'agent.metrics.tokens'
  | 'agent.metrics.toolCalls'
  | 'agent.metrics.durationSec'
  | 'agent.metrics.appliedActions'
  | 'agent.metrics.skippedActions'
  | 'agent.metrics.warnings'
  | 'agent.errors.title'
  | 'agent.errors.taskRequired'
  | 'agent.errors.planFailed'
  | 'agent.errors.executeFailed'
  | 'agent.errors.cancelFailed'
  | 'skills.pageTitle'
  | 'skills.pageDescription'
  | 'skills.searchPlaceholder'
  | 'skills.tab.marketplace'
  | 'skills.tab.mySkills'
  | 'skills.actions.refresh'
  | 'skills.actions.newSkill'
  | 'skills.actions.edit'
  | 'skills.actions.delete'
  | 'skills.actions.save'
  | 'skills.actions.cancel'
  | 'skills.actions.pickFile'
  | 'skills.marketplace.empty'
  | 'skills.mySkills.empty'
  | 'skills.form.name'
  | 'skills.form.description'
  | 'skills.form.triggers'
  | 'skills.form.tools'
  | 'skills.form.planTemplate'
  | 'skills.form.inputsSchema'
  | 'skills.form.outputsSchema'
  | 'skills.admin.importTitle'
  | 'skills.admin.mode'
  | 'skills.admin.mode.upsert'
  | 'skills.admin.mode.insertOnly'
  | 'skills.admin.jsonPlaceholder'
  | 'skills.admin.import'
  | 'skills.admin.results'
  | 'skills.validation.required'
  | 'skills.feedback.saved'
  | 'skills.feedback.saveFailed'
  | 'skills.feedback.deleted'
  | 'skills.feedback.emptyImport'
  | 'skills.feedback.invalidImport'
  | 'skills.feedback.imported'
  | 'skills.feedback.importFailed'
  | 'skills.dialog.deleteTitle'
  | 'skills.dialog.deleteContentPrefix'
  | 'settings.pageTitle'
  | 'settings.pageDescription'
  | 'settings.tab.appearance'
  | 'settings.tab.uploads'
  | 'settings.tab.files'
  | 'settings.tab.notifications'
  | 'settings.tab.security'
  | 'settings.tab.advanced'
  | 'settings.section.appearance'
  | 'settings.section.uploads'
  | 'settings.section.files'
  | 'settings.section.notifications'
  | 'settings.section.security'
  | 'settings.section.advanced'
  | 'settings.language.label'
  | 'settings.language.description'
  | 'settings.language.saving'
  | 'settings.language.updateFailed'
  | 'settings.confirmReset'
  | 'settings.importSuccess'
  | 'settings.importFailed'
  | 'settings.actions.title'
  | 'settings.actions.export'
  | 'settings.actions.import'
  | 'settings.actions.reset'
  | 'files.toolbar.view.list'
  | 'files.toolbar.view.grid'
  | 'files.toolbar.searchTag'
  | 'files.toolbar.searchPlaceholder'
  | 'files.toolbar.clear'
  | 'files.toolbar.sort'
  | 'files.toolbar.sort.name'
  | 'files.toolbar.sort.size'
  | 'files.toolbar.sort.updated'
  | 'files.toolbar.newFolder'
  | 'files.toolbar.upload'
  | 'files.toolbar.aria.list'
  | 'files.toolbar.aria.grid'
  | 'files.toast.newFolderCanceled'
  | 'files.preview.close'
  | 'files.preview.title'
  | 'files.empty.loading'
  | 'files.empty.folderEmpty'
  | 'files.empty.emptyHint'
  | 'files.empty.noMatch'
  | 'files.drag.dropToUpload'
  | 'files.upload.queueTitle'
  | 'files.bulk.selected'
  | 'files.bulk.move'
  | 'files.bulk.download'
  | 'files.bulk.delete'
  | 'files.bulk.clear'
  | 'files.table.col.name'
  | 'files.table.col.size'
  | 'files.table.col.updated'
  | 'files.table.aria.star'
  | 'files.table.aria.unstar'
  | 'files.table.aria.rowActions'
  | 'files.table.aria.cardActions'
  | 'files.action.download'
  | 'files.action.extract'
  | 'files.action.rename'
  | 'files.action.move'
  | 'files.action.share'
  | 'files.action.delete'
  | 'files.action.star'
  | 'files.action.unstar'
  | 'files.folder.loading'
  | 'files.folder.noSubfolders'
  | 'files.upload.toast.success'
  | 'files.upload.toast.failed'
  | 'files.upload.toast.unknownError'
  | 'files.root.myFiles'
  | 'files.owner.you'
  | 'footer.termsOfService'
  | 'footer.privacyPolicy';

type LocaleMessages = Record<LocaleKey, string>;

export const DEFAULT_LANGUAGE: AppLanguage = 'zh-CN';

export const LOCALE_MESSAGES: Record<AppLanguage, LocaleMessages> = {
  'zh-CN': {
    'common.language.zhCN': '简体中文',
    'common.language.enUS': 'English',
    'header.expandSidebar': '展开侧边栏',
    'header.collapseSidebar': '收起侧边栏',
    'header.brandSubtitle': '云端工作空间',
    'header.searchPlaceholder': '搜索文件、文件夹与共享内容',
    'header.toggleTheme': '切换主题',
    'header.hidePreviewPanel': '隐藏预览面板',
    'header.showPreviewPanel': '显示预览面板',
    'header.userMenu': '用户菜单',
    'header.menu.profile': '个人资料',
    'header.menu.settings': '设置',
    'header.menu.dashboard': '仪表盘',
    'header.menu.logout': '退出登录',
    'header.menu.admin': '管理员',
    'header.menu.defaultUserName': '用户',
    'header.menu.defaultEmail': 'user@example.com',
    'sidebar.myFiles': '我的文件',
    'sidebar.shared': '共享',
    'sidebar.recycleBin': '回收站',
    'sidebar.workspaceTree': '工作区目录',
    'sidebar.storage': '存储',
    'sidebar.skills': '技能',
    'sidebar.agent': 'Agent',
    'agent.pageTitle': 'Cloud Agent',
    'agent.pageDescription': '以云端 Agent 模式规划并执行文件操作。',
    'agent.nav.workspace': '工作台',
    'agent.nav.skills': 'Skills',
    'agent.workspace.controls': '任务与策略',
    'agent.workspace.advancedSettings': '高级设置',
    'agent.workspace.planPreview': '规划预览',
    'agent.workspace.executionResult': '执行结果',
    'agent.workspace.emptyPlan': '输入任务后点击“生成计划”，在这里查看规划结果。',
    'agent.workspace.executing': 'Agent 正在执行计划，请稍候…',
    'agent.workspace.emptyExecution': '还没有执行结果。',
    'agent.fields.task': '任务描述',
    'agent.fields.taskPlaceholder': '例如：把 Downloads 中的图片按年月归档到 Photos',
    'agent.fields.executionPolicy': '执行策略',
    'agent.fields.allowFileContent': '允许读取文件内容',
    'agent.fields.maxReadBytes': '单文件最大读取字节',
    'agent.fields.allowedMimeTypes': '允许 MIME Types',
    'agent.fields.maxSteps': '最大步骤数',
    'agent.fields.budgetTokens': 'Token 预算',
    'agent.fields.planHash': 'Plan Hash',
    'agent.fields.chosenSkill': '已选 Skill',
    'agent.actions.plan': '生成计划',
    'agent.actions.reset': '重置',
    'agent.actions.execute': '确认执行',
    'agent.actions.cancel': '取消任务',
    'agent.actions.cancelled': '任务已取消。',
    'agent.metrics.planStatus': 'Plan 状态',
    'agent.metrics.executeStatus': 'Execute 状态',
    'agent.metrics.actions': '步骤数',
    'agent.metrics.tokens': '预估 Tokens',
    'agent.metrics.toolCalls': '工具调用',
    'agent.metrics.durationSec': '预估耗时(秒)',
    'agent.metrics.appliedActions': '已执行步骤',
    'agent.metrics.skippedActions': '跳过步骤',
    'agent.metrics.warnings': '警告',
    'agent.errors.title': 'Agent 运行异常',
    'agent.errors.taskRequired': '请先输入任务描述。',
    'agent.errors.planFailed': '生成计划失败，请稍后重试。',
    'agent.errors.executeFailed': '执行计划失败，请检查反馈后重试。',
    'agent.errors.cancelFailed': '取消任务失败。',
    'skills.pageTitle': '技能',
    'skills.pageDescription': '浏览全局技能市场，并管理你的私有自定义技能。',
    'skills.searchPlaceholder': '搜索技能（name/description/triggers）',
    'skills.tab.marketplace': '技能市场',
    'skills.tab.mySkills': '我的技能',
    'skills.actions.refresh': '刷新',
    'skills.actions.newSkill': '新增技能',
    'skills.actions.edit': '编辑',
    'skills.actions.delete': '删除',
    'skills.actions.save': '保存',
    'skills.actions.cancel': '取消',
    'skills.actions.pickFile': '选择 JSON 文件',
    'skills.marketplace.empty': '没有找到技能市场内容。',
    'skills.mySkills.empty': '还没有私有技能，可以先新增一个。',
    'skills.form.name': '名称',
    'skills.form.description': '描述',
    'skills.form.triggers': '触发词',
    'skills.form.tools': '工具白名单',
    'skills.form.planTemplate': '计划模板',
    'skills.form.inputsSchema': '输入 Schema',
    'skills.form.outputsSchema': '输出 Schema',
    'skills.admin.importTitle': '导入全局技能 (Admin)',
    'skills.admin.mode': '模式',
    'skills.admin.mode.upsert': 'Upsert',
    'skills.admin.mode.insertOnly': 'Insert only',
    'skills.admin.jsonPlaceholder': '粘贴 JSON（数组）或 { items: [] }',
    'skills.admin.import': '导入',
    'skills.admin.results': '导入结果',
    'skills.validation.required': '名称和描述为必填项。',
    'skills.feedback.saved': 'Skill 已保存。',
    'skills.feedback.saveFailed': 'Skill 保存失败。',
    'skills.feedback.deleted': 'Skill 已删除。',
    'skills.feedback.emptyImport': '请先粘贴或选择导入 JSON。',
    'skills.feedback.invalidImport': '导入 JSON 格式错误，需要为数组或 { items: [] }。',
    'skills.feedback.imported': 'Skill 导入完成。',
    'skills.feedback.importFailed': 'Skill 导入失败。',
    'skills.dialog.deleteTitle': '删除 Skill',
    'skills.dialog.deleteContentPrefix': '确认删除 Skill',
    'settings.pageTitle': '设置',
    'settings.pageDescription': '个性化您的 fileflash 体验，管理应用行为和偏好。',
    'settings.tab.appearance': '外观',
    'settings.tab.uploads': '上传',
    'settings.tab.files': '文件管理',
    'settings.tab.notifications': '通知',
    'settings.tab.security': '安全',
    'settings.tab.advanced': '高级',
    'settings.section.appearance': '外观设置',
    'settings.section.uploads': '上传设置',
    'settings.section.files': '文件管理设置',
    'settings.section.notifications': '通知设置',
    'settings.section.security': '安全设置',
    'settings.section.advanced': '高级设置',
    'settings.language.label': '界面语言',
    'settings.language.description': '此偏好会保存到个人设置中，并在下次登录后生效。',
    'settings.language.saving': '保存中...',
    'settings.language.updateFailed': '语言偏好保存失败，请稍后重试。',
    'settings.confirmReset': '确定要重置所有设置到默认值吗？此操作无法撤销。',
    'settings.importSuccess': '设置导入成功！',
    'settings.importFailed': '设置导入失败，请检查文件格式。',
    'settings.actions.title': '设置管理',
    'settings.actions.export': '导出设置',
    'settings.actions.import': '导入设置',
    'settings.actions.reset': '重置所有设置',
    'files.toolbar.view.list': '列表',
    'files.toolbar.view.grid': '网格',
    'files.toolbar.searchTag': '搜索',
    'files.toolbar.searchPlaceholder': '搜索当前文件夹',
    'files.toolbar.clear': '清除',
    'files.toolbar.sort': '排序',
    'files.toolbar.sort.name': '名称',
    'files.toolbar.sort.size': '大小',
    'files.toolbar.sort.updated': '更新时间',
    'files.toolbar.newFolder': '新建文件夹',
    'files.toolbar.upload': '上传',
    'files.toolbar.aria.list': '列表视图',
    'files.toolbar.aria.grid': '网格视图',
    'files.toast.newFolderCanceled': '已取消新建文件夹',
    'files.preview.close': '关闭预览',
    'files.preview.title': '文件预览',
    'files.empty.loading': '加载中',
    'files.empty.folderEmpty': '此文件夹为空',
    'files.empty.emptyHint': '上传文件或创建文件夹。',
    'files.empty.noMatch': '未找到匹配项',
    'files.drag.dropToUpload': '松开以上传文件',
    'files.upload.queueTitle': '上传队列',
    'files.bulk.selected': '已选',
    'files.bulk.move': '移动',
    'files.bulk.download': '下载',
    'files.bulk.delete': '删除',
    'files.bulk.clear': '清除',
    'files.table.col.name': '名称',
    'files.table.col.size': '大小',
    'files.table.col.updated': '更新时间',
    'files.table.aria.star': '标记收藏',
    'files.table.aria.unstar': '取消收藏',
    'files.table.aria.rowActions': '行操作',
    'files.table.aria.cardActions': '卡片操作',
    'files.action.download': '下载',
    'files.action.extract': '解压',
    'files.action.rename': '重命名',
    'files.action.move': '移动',
    'files.action.share': '分享',
    'files.action.delete': '删除',
    'files.action.star': '收藏',
    'files.action.unstar': '取消收藏',
    'files.folder.loading': '加载中...',
    'files.folder.noSubfolders': '暂无子文件夹',
    'files.upload.toast.success': '已上传 {fileName}。',
    'files.upload.toast.failed': '上传 {fileName} 失败：{reason}',
    'files.upload.toast.unknownError': '未知错误',
    'files.root.myFiles': '我的文件',
    'files.owner.you': '你',
    'footer.termsOfService': '使用条款',
    'footer.privacyPolicy': '隐私政策',
  },
  'en-US': {
    'common.language.zhCN': 'Simplified Chinese',
    'common.language.enUS': 'English',
    'header.expandSidebar': 'Expand sidebar',
    'header.collapseSidebar': 'Collapse sidebar',
    'header.brandSubtitle': 'Cloud Workspace',
    'header.searchPlaceholder': 'Search files, folders, and shared content',
    'header.toggleTheme': 'Toggle theme',
    'header.hidePreviewPanel': 'Hide preview panel',
    'header.showPreviewPanel': 'Show preview panel',
    'header.userMenu': 'User menu',
    'header.menu.profile': 'Profile',
    'header.menu.settings': 'Settings',
    'header.menu.dashboard': 'Dashboard',
    'header.menu.logout': 'Log out',
    'header.menu.admin': 'Admin',
    'header.menu.defaultUserName': 'User',
    'header.menu.defaultEmail': 'user@example.com',
    'sidebar.myFiles': 'My Files',
    'sidebar.shared': 'Shared',
    'sidebar.recycleBin': 'Recycle Bin',
    'sidebar.workspaceTree': 'Workspace Tree',
    'sidebar.storage': 'Storage',
    'sidebar.skills': 'Skills',
    'sidebar.agent': 'Agent',
    'agent.pageTitle': 'Cloud Agent',
    'agent.pageDescription': 'Plan and execute cloud agent workflows for file operations.',
    'agent.nav.workspace': 'Workspace',
    'agent.nav.skills': 'Skills',
    'agent.workspace.controls': 'Task & Policy',
    'agent.workspace.advancedSettings': 'Advanced Settings',
    'agent.workspace.planPreview': 'Plan Preview',
    'agent.workspace.executionResult': 'Execution Result',
    'agent.workspace.emptyPlan': 'Describe a task and click Plan to generate the action plan.',
    'agent.workspace.executing': 'Agent is executing this plan. Please wait...',
    'agent.workspace.emptyExecution': 'No execution result yet.',
    'agent.fields.task': 'Task Prompt',
    'agent.fields.taskPlaceholder': 'For example: organize images from Downloads into Photos by month',
    'agent.fields.executionPolicy': 'Execution Policy',
    'agent.fields.allowFileContent': 'Allow file content reads',
    'agent.fields.maxReadBytes': 'Max read bytes per file',
    'agent.fields.allowedMimeTypes': 'Allowed MIME Types',
    'agent.fields.maxSteps': 'Max Steps',
    'agent.fields.budgetTokens': 'Token Budget',
    'agent.fields.planHash': 'Plan Hash',
    'agent.fields.chosenSkill': 'Chosen Skill',
    'agent.actions.plan': 'Create Plan',
    'agent.actions.reset': 'Reset',
    'agent.actions.execute': 'Execute Plan',
    'agent.actions.cancel': 'Cancel Job',
    'agent.actions.cancelled': 'Job cancelled.',
    'agent.metrics.planStatus': 'Plan Status',
    'agent.metrics.executeStatus': 'Execute Status',
    'agent.metrics.actions': 'Actions',
    'agent.metrics.tokens': 'Estimated Tokens',
    'agent.metrics.toolCalls': 'Tool Calls',
    'agent.metrics.durationSec': 'Duration (sec)',
    'agent.metrics.appliedActions': 'Applied Actions',
    'agent.metrics.skippedActions': 'Skipped Actions',
    'agent.metrics.warnings': 'Warnings',
    'agent.errors.title': 'Agent Error',
    'agent.errors.taskRequired': 'Please enter a task prompt first.',
    'agent.errors.planFailed': 'Failed to generate plan. Please retry.',
    'agent.errors.executeFailed': 'Failed to execute plan. Please retry.',
    'agent.errors.cancelFailed': 'Failed to cancel job.',
    'skills.pageTitle': 'Skills',
    'skills.pageDescription': 'Browse the global marketplace and manage your private custom skills.',
    'skills.searchPlaceholder': 'Search skills (name/description/triggers)',
    'skills.tab.marketplace': 'Marketplace',
    'skills.tab.mySkills': 'My Skills',
    'skills.actions.refresh': 'Refresh',
    'skills.actions.newSkill': 'New Skill',
    'skills.actions.edit': 'Edit',
    'skills.actions.delete': 'Delete',
    'skills.actions.save': 'Save',
    'skills.actions.cancel': 'Cancel',
    'skills.actions.pickFile': 'Pick JSON File',
    'skills.marketplace.empty': 'No marketplace skills found.',
    'skills.mySkills.empty': 'No private skills yet. Create one to get started.',
    'skills.form.name': 'Name',
    'skills.form.description': 'Description',
    'skills.form.triggers': 'Triggers',
    'skills.form.tools': 'Tool whitelist',
    'skills.form.planTemplate': 'Plan template',
    'skills.form.inputsSchema': 'Inputs schema',
    'skills.form.outputsSchema': 'Outputs schema',
    'skills.admin.importTitle': 'Import global skills (Admin)',
    'skills.admin.mode': 'Mode',
    'skills.admin.mode.upsert': 'Upsert',
    'skills.admin.mode.insertOnly': 'Insert only',
    'skills.admin.jsonPlaceholder': 'Paste JSON array or { items: [] }',
    'skills.admin.import': 'Import',
    'skills.admin.results': 'Import results',
    'skills.validation.required': 'Name and description are required.',
    'skills.feedback.saved': 'Skill saved successfully.',
    'skills.feedback.saveFailed': 'Failed to save skill.',
    'skills.feedback.deleted': 'Skill deleted.',
    'skills.feedback.emptyImport': 'Paste or upload import JSON first.',
    'skills.feedback.invalidImport': 'Import JSON must be an array or { items: [] }.',
    'skills.feedback.imported': 'Skill import completed.',
    'skills.feedback.importFailed': 'Import failed.',
    'skills.dialog.deleteTitle': 'Delete Skill',
    'skills.dialog.deleteContentPrefix': 'Delete skill',
    'settings.pageTitle': 'Settings',
    'settings.pageDescription': 'Personalize your fileflash experience and manage app behavior.',
    'settings.tab.appearance': 'Appearance',
    'settings.tab.uploads': 'Uploads',
    'settings.tab.files': 'File Management',
    'settings.tab.notifications': 'Notifications',
    'settings.tab.security': 'Security',
    'settings.tab.advanced': 'Advanced',
    'settings.section.appearance': 'Appearance Settings',
    'settings.section.uploads': 'Upload Settings',
    'settings.section.files': 'File Management Settings',
    'settings.section.notifications': 'Notification Settings',
    'settings.section.security': 'Security Settings',
    'settings.section.advanced': 'Advanced Settings',
    'settings.language.label': 'Interface Language',
    'settings.language.description': 'This preference is stored as part of your account settings.',
    'settings.language.saving': 'Saving...',
    'settings.language.updateFailed': 'Failed to save language preference. Please retry.',
    'settings.confirmReset': 'Reset all settings to defaults? This action cannot be undone.',
    'settings.importSuccess': 'Settings imported successfully.',
    'settings.importFailed': 'Failed to import settings. Please verify the JSON format.',
    'settings.actions.title': 'Settings Management',
    'settings.actions.export': 'Export Settings',
    'settings.actions.import': 'Import Settings',
    'settings.actions.reset': 'Reset All Settings',
    'files.toolbar.view.list': 'List',
    'files.toolbar.view.grid': 'Grid',
    'files.toolbar.searchTag': 'Search',
    'files.toolbar.searchPlaceholder': 'Search this folder',
    'files.toolbar.clear': 'Clear',
    'files.toolbar.sort': 'Sort',
    'files.toolbar.sort.name': 'Name',
    'files.toolbar.sort.size': 'Size',
    'files.toolbar.sort.updated': 'Updated',
    'files.toolbar.newFolder': 'New Folder',
    'files.toolbar.upload': 'Upload',
    'files.toolbar.aria.list': 'List view',
    'files.toolbar.aria.grid': 'Grid view',
    'files.toast.newFolderCanceled': 'New folder canceled.',
    'files.preview.close': 'Close preview',
    'files.preview.title': 'File preview',
    'files.empty.loading': 'Loading',
    'files.empty.folderEmpty': 'This folder is empty',
    'files.empty.emptyHint': 'Upload files or create a folder.',
    'files.empty.noMatch': 'No matches for',
    'files.drag.dropToUpload': 'Drop files to upload',
    'files.upload.queueTitle': 'Upload Queue',
    'files.bulk.selected': 'Selected',
    'files.bulk.move': 'Move',
    'files.bulk.download': 'Download',
    'files.bulk.delete': 'Delete',
    'files.bulk.clear': 'Clear',
    'files.table.col.name': 'Name',
    'files.table.col.size': 'Size',
    'files.table.col.updated': 'Updated',
    'files.table.aria.star': 'Star',
    'files.table.aria.unstar': 'Unstar',
    'files.table.aria.rowActions': 'Row actions',
    'files.table.aria.cardActions': 'Card actions',
    'files.action.download': 'Download',
    'files.action.extract': 'Extract',
    'files.action.rename': 'Rename',
    'files.action.move': 'Move',
    'files.action.share': 'Share',
    'files.action.delete': 'Delete',
    'files.action.star': 'Star',
    'files.action.unstar': 'Unstar',
    'files.folder.loading': 'Loading...',
    'files.folder.noSubfolders': 'No subfolders',
    'files.upload.toast.success': 'Uploaded {fileName}.',
    'files.upload.toast.failed': 'Upload of {fileName} failed: {reason}',
    'files.upload.toast.unknownError': 'Unknown error',
    'files.root.myFiles': 'My Files',
    'files.owner.you': 'You',
    'footer.termsOfService': 'Terms of Service',
    'footer.privacyPolicy': 'Privacy Policy',
  },
};
