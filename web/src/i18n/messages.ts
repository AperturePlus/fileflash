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
  | 'files.rename.toast.createdFolder'
  | 'files.rename.toast.createFailed'
  | 'files.rename.toast.renamed'
  | 'files.rename.toast.renameFailed'
  | 'files.delete.confirm.title'
  | 'files.delete.confirm.message'
  | 'files.delete.confirm.confirmText'
  | 'files.delete.toast.success'
  | 'files.delete.toast.failed'
  | 'files.move.toast.noMovable'
  | 'files.move.toast.failedNoneMoved'
  | 'files.move.toast.partial'
  | 'files.move.toast.success'
  | 'files.move.toast.failed'
  | 'files.move.reason.noneMoved'
  | 'files.move.reason.someFailed'
  | 'files.move.toast.selectAtLeastOne'
  | 'files.download.toast.failed'
  | 'files.batch.download.toast.success'
  | 'files.batch.download.toast.failed'
  | 'files.batch.delete.confirm.title'
  | 'files.batch.delete.confirm.message'
  | 'files.batch.delete.confirm.confirmText'
  | 'files.batch.delete.toast.success'
  | 'files.batch.delete.toast.failed'
  | 'files.root.myFiles'
  | 'files.owner.you'
  | 'sharing.page.title'
  | 'sharing.page.description'
  | 'sharing.tab.sharedWithMe'
  | 'sharing.tab.myShareLinks'
  | 'sharing.empty.received'
  | 'sharing.empty.links'
  | 'sharing.itemType.file'
  | 'sharing.itemType.folder'
  | 'sharing.permission.read'
  | 'sharing.permission.write'
  | 'sharing.permission.admin'
  | 'sharing.table.received.name'
  | 'sharing.table.received.sharedBy'
  | 'sharing.table.received.permission'
  | 'sharing.table.received.sharedAt'
  | 'sharing.table.received.accept'
  | 'sharing.table.links.resource'
  | 'sharing.table.links.shareLink'
  | 'sharing.table.links.visitsDownloads'
  | 'sharing.table.links.createdAt'
  | 'sharing.table.links.copy'
  | 'sharing.table.links.delete'
  | 'sharing.batch.selected'
  | 'sharing.batch.acceptSelected'
  | 'sharing.batch.clear'
  | 'sharing.confirm.deleteLink.title'
  | 'sharing.confirm.deleteLink.message'
  | 'sharing.confirm.deleteLink.confirm'
  | 'sharing.toast.linkDeleted'
  | 'sharing.toast.linkDeleteFailed'
  | 'sharing.toast.linkCopied'
  | 'sharing.copyDialog.title'
  | 'sharing.copyDialog.message'
  | 'trash.page.title'
  | 'trash.page.description'
  | 'trash.page.clearBin'
  | 'trash.page.empty'
  | 'trash.confirm.restore.title'
  | 'trash.confirm.restore.message'
  | 'trash.confirm.restore.confirm'
  | 'trash.confirm.delete.title'
  | 'trash.confirm.delete.message'
  | 'trash.confirm.delete.confirm'
  | 'trash.confirm.clear.title'
  | 'trash.confirm.clear.message'
  | 'trash.confirm.clear.confirm'
  | 'trash.toast.restored'
  | 'trash.toast.restoreFailed'
  | 'trash.toast.deleted'
  | 'trash.toast.deleteFailed'
  | 'trash.toast.cleared'
  | 'trash.toast.clearFailed'
  | 'trash.table.name'
  | 'trash.table.originalLocation'
  | 'trash.table.deletedAt'
  | 'trash.table.expiresIn'
  | 'trash.table.days'
  | 'trash.table.restore'
  | 'trash.table.delete'
  | 'share.page.title'
  | 'share.page.linkCode'
  | 'share.page.saveDialogTitle'
  | 'share.page.saveDialogConfirm'
  | 'share.page.needAccessFirst'
  | 'share.itemType.file'
  | 'share.itemType.folder'
  | 'share.info.type'
  | 'share.info.name'
  | 'share.info.size'
  | 'share.info.expires'
  | 'share.info.password'
  | 'share.info.never'
  | 'share.info.passwordRequired'
  | 'share.info.passwordNotRequired'
  | 'share.access.title'
  | 'share.access.passwordLabel'
  | 'share.access.passwordPlaceholder'
  | 'share.access.checking'
  | 'share.access.unlock'
  | 'share.access.accessing'
  | 'share.access.getAccess'
  | 'share.actions.title'
  | 'share.actions.loading'
  | 'share.actions.preview'
  | 'share.actions.downloading'
  | 'share.actions.download'
  | 'share.actions.saving'
  | 'share.actions.saveFolder'
  | 'share.actions.save'
  | 'share.status.loadFailed'
  | 'share.status.accessGranted'
  | 'share.status.invalidPasswordOrExpired'
  | 'share.status.expiredOrUnavailable'
  | 'share.status.downloadFailed'
  | 'share.status.previewFailed'
  | 'share.status.savedSuccess'
  | 'share.status.saveFailed'
  | 'share.dialog.title'
  | 'share.dialog.subtitle'
  | 'share.dialog.close'
  | 'share.dialog.section.collaborators'
  | 'share.dialog.searchPlaceholder'
  | 'share.dialog.searching'
  | 'share.dialog.result.userGroup'
  | 'share.dialog.emptyCollaborators'
  | 'share.dialog.collaborator.user'
  | 'share.dialog.collaborator.group'
  | 'share.dialog.permission.read'
  | 'share.dialog.permission.write'
  | 'share.dialog.permission.admin'
  | 'share.dialog.remove'
  | 'share.dialog.section.publicLink'
  | 'share.dialog.publicDescription'
  | 'share.dialog.generatingLink'
  | 'share.dialog.copy'
  | 'share.dialog.passwordProtected'
  | 'share.dialog.passwordPlaceholder'
  | 'share.dialog.regenerate'
  | 'share.dialog.allowDownload'
  | 'share.dialog.allowPreview'
  | 'share.dialog.expireDate'
  | 'share.dialog.clear'
  | 'share.dialog.saving'
  | 'share.dialog.saveSettings'
  | 'share.dialog.settings.passwordUpdated'
  | 'share.dialog.settings.saved'
  | 'share.dialog.settings.saveFailed'
  | 'share.dialog.settings.regenerated'
  | 'share.dialog.settings.regenerateFailed'
  | 'share.dialog.settings.passwordCopied'
  | 'share.dialog.settings.linkCopied'
  | 'share.dialog.copyPassword.title'
  | 'share.dialog.copyPassword.message'
  | 'share.dialog.copyLink.title'
  | 'share.dialog.copyLink.message'
  | 'share.dialog.publicHiddenNotice'
  | 'share.dialog.done'
  | 'move.dialog.title.single'
  | 'move.dialog.title.multiple'
  | 'move.dialog.title.default'
  | 'move.dialog.prompt'
  | 'move.dialog.confirm'
  | 'move.dialog.root'
  | 'move.dialog.selectDestinationWarning'
  | 'move.dialog.shareHandling.title'
  | 'move.dialog.shareHandling.keep'
  | 'move.dialog.shareHandling.revoke'
  | 'move.dialog.loading'
  | 'move.dialog.empty'
  | 'move.dialog.cancel'
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
    'files.rename.toast.createdFolder': '已创建文件夹“{folderName}”。',
    'files.rename.toast.createFailed': '创建文件夹失败。',
    'files.rename.toast.renamed': '已重命名为“{newName}”。',
    'files.rename.toast.renameFailed': '重命名失败。',
    'files.delete.confirm.title': '移动到回收站',
    'files.delete.confirm.message': '将“{itemName}”移动到回收站？',
    'files.delete.confirm.confirmText': '移动',
    'files.delete.toast.success': '“{itemName}”已移动到回收站。',
    'files.delete.toast.failed': '移动到回收站失败。',
    'files.move.toast.noMovable': '没有可移动的项目。',
    'files.move.toast.failedNoneMoved': '移动失败。{reason}',
    'files.move.toast.partial': '已移动 {succeeded}/{processed}。{reason}',
    'files.move.toast.success': '已移动 {count} 个项目。',
    'files.move.toast.failed': '批量移动失败。',
    'files.move.reason.noneMoved': '没有项目被移动。',
    'files.move.reason.someFailed': '部分项目移动失败。',
    'files.move.toast.selectAtLeastOne': '请至少选择一个项目。',
    'files.download.toast.failed': '下载失败。',
    'files.batch.download.toast.success': '已下载 {count} 个项目。',
    'files.batch.download.toast.failed': '下载所选文件失败。',
    'files.batch.delete.confirm.title': '移动到回收站',
    'files.batch.delete.confirm.message': '将所选的 {count} 个项目移动到回收站？',
    'files.batch.delete.confirm.confirmText': '移动',
    'files.batch.delete.toast.success': '已将 {count} 个项目移动到回收站。',
    'files.batch.delete.toast.failed': '移动所选项目到回收站失败。',
    'files.root.myFiles': '我的文件',
    'files.owner.you': '你',
    'sharing.page.title': '共享中心',
    'sharing.page.description': '管理收到的共享内容和你创建的共享链接。',
    'sharing.tab.sharedWithMe': '共享给我',
    'sharing.tab.myShareLinks': '我的共享链接',
    'sharing.empty.received': '还没有收到共享文件。',
    'sharing.empty.links': '还没有创建共享链接。',
    'sharing.itemType.file': '文件',
    'sharing.itemType.folder': '文件夹',
    'sharing.permission.read': '只读',
    'sharing.permission.write': '可编辑',
    'sharing.permission.admin': '管理员',
    'sharing.table.received.name': '名称',
    'sharing.table.received.sharedBy': '共享人',
    'sharing.table.received.permission': '权限',
    'sharing.table.received.sharedAt': '共享时间',
    'sharing.table.received.accept': '接收',
    'sharing.table.links.resource': '资源',
    'sharing.table.links.shareLink': '共享链接',
    'sharing.table.links.visitsDownloads': '访问 / 下载',
    'sharing.table.links.createdAt': '创建时间',
    'sharing.table.links.copy': '复制',
    'sharing.table.links.delete': '删除',
    'sharing.batch.selected': '已选',
    'sharing.batch.acceptSelected': '接收所选',
    'sharing.batch.clear': '清除',
    'sharing.confirm.deleteLink.title': '删除共享链接',
    'sharing.confirm.deleteLink.message': '确定删除共享链接 {shareLink} 吗？',
    'sharing.confirm.deleteLink.confirm': '删除',
    'sharing.toast.linkDeleted': '共享链接已删除。',
    'sharing.toast.linkDeleteFailed': '删除共享链接失败。',
    'sharing.toast.linkCopied': '共享链接已复制。',
    'sharing.copyDialog.title': '复制共享链接',
    'sharing.copyDialog.message': '剪贴板不可用，请手动复制此链接：',
    'trash.page.title': '回收站',
    'trash.page.description': '项目会保留最多 30 天，之后系统会自动清理。',
    'trash.page.clearBin': '清空回收站',
    'trash.page.empty': '回收站为空。',
    'trash.confirm.restore.title': '恢复项目',
    'trash.confirm.restore.message': '确定恢复“{itemName}”吗？',
    'trash.confirm.restore.confirm': '恢复',
    'trash.confirm.delete.title': '永久删除',
    'trash.confirm.delete.message': '确定永久删除“{itemName}”吗？此操作无法撤销。',
    'trash.confirm.delete.confirm': '删除',
    'trash.confirm.clear.title': '清空回收站',
    'trash.confirm.clear.message': '确定清空整个回收站吗？此操作无法撤销。',
    'trash.confirm.clear.confirm': '清空',
    'trash.toast.restored': '已恢复“{itemName}”。',
    'trash.toast.restoreFailed': '恢复失败。',
    'trash.toast.deleted': '已删除“{itemName}”。',
    'trash.toast.deleteFailed': '永久删除失败。',
    'trash.toast.cleared': '回收站已清空。',
    'trash.toast.clearFailed': '清空回收站失败。',
    'trash.table.name': '名称',
    'trash.table.originalLocation': '原始位置',
    'trash.table.deletedAt': '删除时间',
    'trash.table.expiresIn': '剩余时间',
    'trash.table.days': '{days} 天',
    'trash.table.restore': '恢复',
    'trash.table.delete': '删除',
    'share.page.title': '共享链接',
    'share.page.linkCode': '链接码：',
    'share.page.saveDialogTitle': '保存到我的空间',
    'share.page.saveDialogConfirm': '保存到此处',
    'share.page.needAccessFirst': '请先获取共享访问权限。',
    'share.itemType.file': '文件',
    'share.itemType.folder': '文件夹',
    'share.info.type': '类型',
    'share.info.name': '名称',
    'share.info.size': '大小',
    'share.info.expires': '有效期',
    'share.info.password': '密码',
    'share.info.never': '永不过期',
    'share.info.passwordRequired': '需要',
    'share.info.passwordNotRequired': '不需要',
    'share.access.title': '访问权限',
    'share.access.passwordLabel': '密码',
    'share.access.passwordPlaceholder': '输入密码',
    'share.access.checking': '校验中...',
    'share.access.unlock': '解锁',
    'share.access.accessing': '访问中...',
    'share.access.getAccess': '获取访问权限',
    'share.actions.title': '操作',
    'share.actions.loading': '加载中...',
    'share.actions.preview': '预览',
    'share.actions.downloading': '下载中...',
    'share.actions.download': '下载',
    'share.actions.saving': '保存中...',
    'share.actions.saveFolder': '将文件夹保存到我的空间',
    'share.actions.save': '保存到我的空间',
    'share.status.loadFailed': '无法加载共享内容，链接可能无效或已过期。',
    'share.status.accessGranted': '访问已授权。',
    'share.status.invalidPasswordOrExpired': '密码错误或共享已过期。',
    'share.status.expiredOrUnavailable': '共享已过期或暂不可用。',
    'share.status.downloadFailed': '下载失败。',
    'share.status.previewFailed': '预览失败。',
    'share.status.savedSuccess': '保存成功（{itemType}）。',
    'share.status.saveFailed': '保存失败，请确认你已登录且邮箱已验证。',
    'share.dialog.title': '共享：{itemName}',
    'share.dialog.subtitle': '管理协作者权限和公开链接访问。',
    'share.dialog.close': '关闭弹窗',
    'share.dialog.section.collaborators': '协作者权限',
    'share.dialog.searchPlaceholder': '搜索用户或用户组',
    'share.dialog.searching': '搜索中...',
    'share.dialog.result.userGroup': '用户组',
    'share.dialog.emptyCollaborators': '暂无协作者。',
    'share.dialog.collaborator.user': '用户',
    'share.dialog.collaborator.group': '用户组',
    'share.dialog.permission.read': '只读',
    'share.dialog.permission.write': '可编辑',
    'share.dialog.permission.admin': '管理员',
    'share.dialog.remove': '移除',
    'share.dialog.section.publicLink': '公开链接',
    'share.dialog.publicDescription': '配置密码、到期时间和下载/预览权限。',
    'share.dialog.generatingLink': '正在生成链接...',
    'share.dialog.copy': '复制',
    'share.dialog.passwordProtected': '密码保护',
    'share.dialog.passwordPlaceholder': '留空则自动生成',
    'share.dialog.regenerate': '重新生成',
    'share.dialog.allowDownload': '允许下载',
    'share.dialog.allowPreview': '允许预览',
    'share.dialog.expireDate': '到期日期',
    'share.dialog.clear': '清除',
    'share.dialog.saving': '保存中...',
    'share.dialog.saveSettings': '保存设置',
    'share.dialog.settings.passwordUpdated': '密码已更新，请及时复制。',
    'share.dialog.settings.saved': '共享设置已保存。',
    'share.dialog.settings.saveFailed': '保存设置失败。',
    'share.dialog.settings.regenerated': '已生成新密码，请及时复制。',
    'share.dialog.settings.regenerateFailed': '重新生成密码失败。',
    'share.dialog.settings.passwordCopied': '密码已复制。',
    'share.dialog.settings.linkCopied': '链接已复制。',
    'share.dialog.copyPassword.title': '复制密码',
    'share.dialog.copyPassword.message': '剪贴板不可用，请手动复制此密码：',
    'share.dialog.copyLink.title': '复制链接',
    'share.dialog.copyLink.message': '剪贴板不可用，请手动复制此链接：',
    'share.dialog.publicHiddenNotice': '当前仅在弹窗中隐藏公开链接，已有链接仍保持可用。',
    'share.dialog.done': '完成',
    'move.dialog.title.single': '移动“{itemName}”',
    'move.dialog.title.multiple': '移动 {count} 个项目',
    'move.dialog.title.default': '移动',
    'move.dialog.prompt': '选择新的位置：',
    'move.dialog.confirm': '移动到此处',
    'move.dialog.root': '我的文件（根目录）',
    'move.dialog.selectDestinationWarning': '请选择目标文件夹。',
    'move.dialog.shareHandling.title': '共享链接处理',
    'move.dialog.shareHandling.keep': '保留现有共享链接',
    'move.dialog.shareHandling.revoke': '移动后撤销现有共享链接',
    'move.dialog.loading': '加载中...',
    'move.dialog.empty': '暂无可用文件夹。',
    'move.dialog.cancel': '取消',
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
    'files.rename.toast.createdFolder': 'Created folder "{folderName}".',
    'files.rename.toast.createFailed': 'Folder creation failed.',
    'files.rename.toast.renamed': 'Renamed to "{newName}".',
    'files.rename.toast.renameFailed': 'Rename failed.',
    'files.delete.confirm.title': 'Move To Trash',
    'files.delete.confirm.message': 'Move "{itemName}" to trash?',
    'files.delete.confirm.confirmText': 'Move',
    'files.delete.toast.success': '"{itemName}" moved to trash.',
    'files.delete.toast.failed': 'Failed to move item to trash.',
    'files.move.toast.noMovable': 'No movable items found.',
    'files.move.toast.failedNoneMoved': 'Move failed. {reason}',
    'files.move.toast.partial': 'Moved {succeeded}/{processed}. {reason}',
    'files.move.toast.success': 'Moved {count} item(s).',
    'files.move.toast.failed': 'Batch move failed.',
    'files.move.reason.noneMoved': 'No items were moved.',
    'files.move.reason.someFailed': 'Some items failed.',
    'files.move.toast.selectAtLeastOne': 'Please select at least one item.',
    'files.download.toast.failed': 'Download failed.',
    'files.batch.download.toast.success': 'Downloaded {count} item(s).',
    'files.batch.download.toast.failed': 'Failed to download selected files.',
    'files.batch.delete.confirm.title': 'Move To Trash',
    'files.batch.delete.confirm.message': 'Move {count} selected item(s) to trash?',
    'files.batch.delete.confirm.confirmText': 'Move',
    'files.batch.delete.toast.success': 'Moved {count} item(s) to trash.',
    'files.batch.delete.toast.failed': 'Failed to move selected items to trash.',
    'files.root.myFiles': 'My Files',
    'files.owner.you': 'You',
    'sharing.page.title': 'Sharing Center',
    'sharing.page.description': 'Manage received items and links you shared with others.',
    'sharing.tab.sharedWithMe': 'Shared With Me',
    'sharing.tab.myShareLinks': 'My Share Links',
    'sharing.empty.received': 'No files shared with you.',
    'sharing.empty.links': 'No share links created yet.',
    'sharing.itemType.file': 'File',
    'sharing.itemType.folder': 'Folder',
    'sharing.permission.read': 'Read',
    'sharing.permission.write': 'Write',
    'sharing.permission.admin': 'Admin',
    'sharing.table.received.name': 'Name',
    'sharing.table.received.sharedBy': 'Shared By',
    'sharing.table.received.permission': 'Permission',
    'sharing.table.received.sharedAt': 'Shared At',
    'sharing.table.received.accept': 'Accept',
    'sharing.table.links.resource': 'Resource',
    'sharing.table.links.shareLink': 'Share Link',
    'sharing.table.links.visitsDownloads': 'Visits / Downloads',
    'sharing.table.links.createdAt': 'Created At',
    'sharing.table.links.copy': 'Copy',
    'sharing.table.links.delete': 'Delete',
    'sharing.batch.selected': 'SELECTED',
    'sharing.batch.acceptSelected': 'Accept Selected',
    'sharing.batch.clear': 'Clear',
    'sharing.confirm.deleteLink.title': 'Delete Share Link',
    'sharing.confirm.deleteLink.message': 'Delete share link {shareLink}?',
    'sharing.confirm.deleteLink.confirm': 'Delete',
    'sharing.toast.linkDeleted': 'Share link deleted.',
    'sharing.toast.linkDeleteFailed': 'Failed to delete share link.',
    'sharing.toast.linkCopied': 'Share link copied.',
    'sharing.copyDialog.title': 'Copy Share Link',
    'sharing.copyDialog.message': 'Clipboard is unavailable. Copy this link manually:',
    'trash.page.title': 'Recycle Bin',
    'trash.page.description': 'Items are kept for up to 30 days before automatic cleanup.',
    'trash.page.clearBin': 'Clear Bin',
    'trash.page.empty': 'Recycle bin is empty.',
    'trash.confirm.restore.title': 'Restore Item',
    'trash.confirm.restore.message': 'Restore "{itemName}"?',
    'trash.confirm.restore.confirm': 'Restore',
    'trash.confirm.delete.title': 'Permanent Delete',
    'trash.confirm.delete.message': 'Permanently delete "{itemName}"? This cannot be undone.',
    'trash.confirm.delete.confirm': 'Delete',
    'trash.confirm.clear.title': 'Clear Recycle Bin',
    'trash.confirm.clear.message': 'Clear entire recycle bin? This cannot be undone.',
    'trash.confirm.clear.confirm': 'Clear',
    'trash.toast.restored': 'Restored "{itemName}".',
    'trash.toast.restoreFailed': 'Restore failed.',
    'trash.toast.deleted': 'Deleted "{itemName}".',
    'trash.toast.deleteFailed': 'Permanent delete failed.',
    'trash.toast.cleared': 'Recycle bin cleared.',
    'trash.toast.clearFailed': 'Clear recycle bin failed.',
    'trash.table.name': 'Name',
    'trash.table.originalLocation': 'Original Location',
    'trash.table.deletedAt': 'Deleted At',
    'trash.table.expiresIn': 'Expires In',
    'trash.table.days': '{days} days',
    'trash.table.restore': 'Restore',
    'trash.table.delete': 'Delete',
    'share.page.title': 'Shared Link',
    'share.page.linkCode': 'Link code:',
    'share.page.saveDialogTitle': 'Save to My Space',
    'share.page.saveDialogConfirm': 'Save Here',
    'share.page.needAccessFirst': 'Please access the share first.',
    'share.itemType.file': 'File',
    'share.itemType.folder': 'Folder',
    'share.info.type': 'Type',
    'share.info.name': 'Name',
    'share.info.size': 'Size',
    'share.info.expires': 'Expires',
    'share.info.password': 'Password',
    'share.info.never': 'Never',
    'share.info.passwordRequired': 'Required',
    'share.info.passwordNotRequired': 'Not required',
    'share.access.title': 'Access',
    'share.access.passwordLabel': 'Password',
    'share.access.passwordPlaceholder': 'Enter password',
    'share.access.checking': 'Checking...',
    'share.access.unlock': 'Unlock',
    'share.access.accessing': 'Accessing...',
    'share.access.getAccess': 'Get Access',
    'share.actions.title': 'Actions',
    'share.actions.loading': 'Loading...',
    'share.actions.preview': 'Preview',
    'share.actions.downloading': 'Downloading...',
    'share.actions.download': 'Download',
    'share.actions.saving': 'Saving...',
    'share.actions.saveFolder': 'Save Folder to My Space',
    'share.actions.save': 'Save to My Space',
    'share.status.loadFailed': 'Unable to load share. The link may be invalid or expired.',
    'share.status.accessGranted': 'Access granted.',
    'share.status.invalidPasswordOrExpired': 'Invalid password or share expired.',
    'share.status.expiredOrUnavailable': 'Share expired or unavailable.',
    'share.status.downloadFailed': 'Download failed.',
    'share.status.previewFailed': 'Preview failed.',
    'share.status.savedSuccess': 'Saved successfully ({itemType}).',
    'share.status.saveFailed': 'Save failed. Please make sure you are logged in and verified.',
    'share.dialog.title': 'Share: {itemName}',
    'share.dialog.subtitle': 'Manage collaborator permissions and public link access.',
    'share.dialog.close': 'Close dialog',
    'share.dialog.section.collaborators': 'Collaborator Permissions',
    'share.dialog.searchPlaceholder': 'Search users or groups',
    'share.dialog.searching': 'Searching...',
    'share.dialog.result.userGroup': 'User group',
    'share.dialog.emptyCollaborators': 'No collaborators configured.',
    'share.dialog.collaborator.user': 'User',
    'share.dialog.collaborator.group': 'Group',
    'share.dialog.permission.read': 'Read',
    'share.dialog.permission.write': 'Write',
    'share.dialog.permission.admin': 'Admin',
    'share.dialog.remove': 'Remove',
    'share.dialog.section.publicLink': 'Public Link',
    'share.dialog.publicDescription': 'Configure password, expiry date, and download/preview permissions.',
    'share.dialog.generatingLink': 'Generating link...',
    'share.dialog.copy': 'Copy',
    'share.dialog.passwordProtected': 'Password protected',
    'share.dialog.passwordPlaceholder': 'Leave blank to auto-generate',
    'share.dialog.regenerate': 'Regenerate',
    'share.dialog.allowDownload': 'Allow download',
    'share.dialog.allowPreview': 'Allow preview',
    'share.dialog.expireDate': 'Expire date',
    'share.dialog.clear': 'Clear',
    'share.dialog.saving': 'Saving...',
    'share.dialog.saveSettings': 'Save settings',
    'share.dialog.settings.passwordUpdated': 'Password updated. Copy it now.',
    'share.dialog.settings.saved': 'Share settings saved.',
    'share.dialog.settings.saveFailed': 'Failed to save settings.',
    'share.dialog.settings.regenerated': 'New password generated. Copy it now.',
    'share.dialog.settings.regenerateFailed': 'Failed to regenerate password.',
    'share.dialog.settings.passwordCopied': 'Password copied.',
    'share.dialog.settings.linkCopied': 'Link copied.',
    'share.dialog.copyPassword.title': 'Copy Password',
    'share.dialog.copyPassword.message': 'Clipboard is unavailable. Copy this password manually:',
    'share.dialog.copyLink.title': 'Copy Link',
    'share.dialog.copyLink.message': 'Clipboard is unavailable. Copy this link manually:',
    'share.dialog.publicHiddenNotice': 'Public link hidden in this dialog. Existing links are kept.',
    'share.dialog.done': 'Done',
    'move.dialog.title.single': 'Move "{itemName}"',
    'move.dialog.title.multiple': 'Move {count} items',
    'move.dialog.title.default': 'Move',
    'move.dialog.prompt': 'Choose a new location:',
    'move.dialog.confirm': 'Move Here',
    'move.dialog.root': 'My Files (Root)',
    'move.dialog.selectDestinationWarning': 'Please select a destination folder.',
    'move.dialog.shareHandling.title': 'Shared Link Handling',
    'move.dialog.shareHandling.keep': 'Keep active share links',
    'move.dialog.shareHandling.revoke': 'Revoke active share links after move',
    'move.dialog.loading': 'Loading...',
    'move.dialog.empty': 'No folders available.',
    'move.dialog.cancel': 'Cancel',
    'footer.termsOfService': 'Terms of Service',
    'footer.privacyPolicy': 'Privacy Policy',
  },
};
