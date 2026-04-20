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
