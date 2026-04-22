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
  | 'settings.actions.reset';

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
    'skills.admin.jsonPlaceholder': 'Paste JSON (array) or { items: [] }',
    'skills.admin.import': 'Import',
    'skills.admin.results': 'Import results',
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
  },
};
