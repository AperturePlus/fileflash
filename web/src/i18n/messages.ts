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
  | 'header.menu.console'
  | 'header.menu.logout'
  | 'header.menu.admin'
  | 'header.menu.defaultUserName'
  | 'header.menu.defaultEmail'
  | 'console.title'
  | 'console.nav.overview'
  | 'console.nav.users'
  | 'console.nav.storage'
  | 'console.nav.content'
  | 'console.nav.moderation'
  | 'console.nav.system'
  | 'console.nav.logs'
  | 'console.nav.notifications'
  | 'console.nav.rules'
  | 'sidebar.myFiles'
  | 'sidebar.shared'
  | 'sidebar.recycleBin'
  | 'sidebar.starred'
  | 'sidebar.starredEmpty'
  | 'sidebar.workspaceTree'
  | 'sidebar.storage'
  | 'sidebar.skills'
  | 'sidebar.agent'
  | 'sidebar.myFiles.uploadingAria'
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
  | 'settings.resetSuccess'
  | 'settings.appearance.theme.label'
  | 'settings.appearance.theme.description'
  | 'settings.appearance.theme.light'
  | 'settings.appearance.theme.dark'
  | 'settings.appearance.compactMode.label'
  | 'settings.appearance.compactMode.description'
  | 'settings.appearance.defaultFileView.label'
  | 'settings.appearance.defaultFileView.description'
  | 'settings.appearance.defaultFileView.option.list'
  | 'settings.appearance.defaultFileView.option.grid'
  | 'settings.appearance.defaultFileView.option.tiles'
  | 'settings.appearance.showFileExtensions.label'
  | 'settings.appearance.showFileExtensions.description'
  | 'settings.uploads.maxConcurrentUploads.label'
  | 'settings.uploads.maxConcurrentUploads.description'
  | 'settings.uploads.chunkSize.label'
  | 'settings.uploads.chunkSize.description'
  | 'settings.uploads.autoRetryFailedUploads.label'
  | 'settings.uploads.autoRetryFailedUploads.description'
  | 'settings.uploads.retryAttempts.label'
  | 'settings.uploads.retryAttempts.description'
  | 'settings.files.itemsPerPage.label'
  | 'settings.files.itemsPerPage.description'
  | 'settings.files.showHiddenFiles.label'
  | 'settings.files.showHiddenFiles.description'
  | 'settings.files.autoRefreshInterval.label'
  | 'settings.files.autoRefreshInterval.description'
  | 'settings.files.autoDeleteDays.label'
  | 'settings.files.autoDeleteDays.description'
  | 'settings.files.autoDeleteDays.option.7'
  | 'settings.files.autoDeleteDays.option.14'
  | 'settings.files.autoDeleteDays.option.30'
  | 'settings.files.autoDeleteDays.option.60'
  | 'settings.files.autoDeleteDays.option.90'
  | 'settings.files.confirmDelete.label'
  | 'settings.files.confirmDelete.description'
  | 'settings.notifications.desktop.label'
  | 'settings.notifications.desktop.description'
  | 'settings.notifications.sound.label'
  | 'settings.notifications.sound.description'
  | 'settings.notifications.uploadComplete.label'
  | 'settings.notifications.uploadComplete.description'
  | 'settings.notifications.error.label'
  | 'settings.notifications.error.description'
  | 'settings.security.sessionTimeout.label'
  | 'settings.security.sessionTimeout.description'
  | 'settings.security.sessionTimeout.option.disabled'
  | 'settings.security.sessionTimeout.option.30m'
  | 'settings.security.sessionTimeout.option.1h'
  | 'settings.security.sessionTimeout.option.2h'
  | 'settings.security.sessionTimeout.option.4h'
  | 'settings.security.sessionTimeout.option.8h'
  | 'settings.security.requirePasswordForSensitiveActions.label'
  | 'settings.security.requirePasswordForSensitiveActions.description'
  | 'settings.advanced.debugMode.label'
  | 'settings.advanced.debugMode.description'
  | 'settings.advanced.cacheDuration.label'
  | 'settings.advanced.cacheDuration.description'
  | 'settings.advanced.cacheDuration.option.1h'
  | 'settings.advanced.cacheDuration.option.6h'
  | 'settings.advanced.cacheDuration.option.12h'
  | 'settings.advanced.cacheDuration.option.24h'
  | 'settings.advanced.cacheDuration.option.72h'
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
  | 'files.upload.action.cancel'
  | 'files.upload.action.resume'
  | 'files.upload.state.hashing'
  | 'files.upload.state.uploading'
  | 'files.upload.state.paused'
  | 'files.upload.state.canceling'
  | 'files.upload.state.succeeded'
  | 'files.upload.state.failed'
  | 'files.upload.state.canceled'
  | 'files.upload.hint.sessionExpired'
  | 'files.upload.hint.needReselect'
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
  | 'files.mediaOptimization.processing'
  | 'files.mediaOptimization.ready'
  | 'files.mediaOptimization.failedFallback'
  | 'files.folder.loading'
  | 'files.folder.noSubfolders'
  | 'files.upload.toast.success'
  | 'files.upload.toast.failed'
  | 'files.upload.toast.unknownError'
  | 'files.star.toast.failed'
  | 'files.star.toast.unknownError'
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
  | 'sharing.table.links.regeneratePassword'
  | 'sharing.table.links.delete'
  | 'sharing.batch.selected'
  | 'sharing.batch.acceptSelected'
  | 'sharing.batch.clear'
  | 'sharing.confirm.deleteLink.title'
  | 'sharing.confirm.deleteLink.message'
  | 'sharing.confirm.deleteLink.confirm'
  | 'sharing.confirm.regeneratePassword.title'
  | 'sharing.confirm.regeneratePassword.message'
  | 'sharing.confirm.regeneratePassword.confirm'
  | 'sharing.toast.linkDeleted'
  | 'sharing.toast.linkDeleteFailed'
  | 'sharing.toast.linkCopied'
  | 'sharing.toast.passwordRegenerated'
  | 'sharing.toast.passwordRegenerateFailed'
  | 'sharing.copyDialog.title'
  | 'sharing.copyDialog.message'
  | 'sharing.passwordDialog.title'
  | 'sharing.passwordDialog.message'
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
  | 'share.dialog.pendingApplyNotice'
  | 'share.dialog.confirmRevoke.title'
  | 'share.dialog.confirmRevoke.message'
  | 'share.dialog.confirmRevoke.confirm'
  | 'share.dialog.generatedPassword.title'
  | 'share.dialog.generatedPassword.message'
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
  | 'files.preview.detail.unknownType'
  | 'files.preview.detail.download'
  | 'files.preview.detail.reload'
  | 'files.preview.detail.loading'
  | 'files.preview.detail.notAvailable'
  | 'files.preview.detail.placeholder'
  | 'files.preview.detail.loadFailed'
  | 'files.preview.detail.downloadFailed'
  | 'files.preview.image.alt'
  | 'files.preview.pdf.prev'
  | 'files.preview.pdf.next'
  | 'files.preview.pdf.page'
  | 'files.preview.pdf.fallbackMode'
  | 'files.preview.pdf.fallbackNote'
  | 'files.preview.pdf.retryRender'
  | 'files.preview.pdf.openNewTab'
  | 'files.preview.pdf.renderFailed'
  | 'files.preview.video.loading'
  | 'files.preview.video.loadFailed'
  | 'files.preview.video.downloadFailed'
  | 'files.preview.video.mimeFallback'
  | 'agent.v2.layout.brand'
  | 'agent.v2.layout.tab.workspace'
  | 'agent.v2.layout.tab.skills'
  | 'agent.v2.sessions.label'
  | 'agent.v2.sessions.new'
  | 'agent.v2.sessions.empty'
  | 'agent.v2.sessions.delete'
  | 'agent.v2.sessions.relative.justNow'
  | 'agent.v2.sessions.relative.minutes'
  | 'agent.v2.sessions.relative.hours'
  | 'agent.v2.sessions.relative.days'
  | 'agent.v2.timeline.label'
  | 'agent.v2.timeline.welcomeHint'
  | 'agent.v2.timeline.hint.organize'
  | 'agent.v2.timeline.hint.duplicates'
  | 'agent.v2.timeline.hint.tagInvoices'
  | 'agent.v2.input.placeholder'
  | 'agent.v2.input.send'
  | 'agent.v2.input.policy.planOnly'
  | 'agent.v2.input.policy.confirm'
  | 'agent.v2.input.policy.autopilot'
  | 'agent.v2.input.reasoning.adaptive'
  | 'agent.v2.input.reasoning.low'
  | 'agent.v2.input.reasoning.medium'
  | 'agent.v2.input.reasoning.high'
  | 'agent.v2.input.reasoning.xhigh'
  | 'agent.v2.input.reasoning.max'
  | 'agent.v2.turn.role'
  | 'agent.v2.turn.status.pending'
  | 'agent.v2.turn.status.running'
  | 'agent.v2.turn.status.succeeded'
  | 'agent.v2.turn.status.failed'
  | 'agent.v2.turn.status.canceled'
  | 'agent.v2.turn.cost.label'
  | 'agent.v2.turn.cost.tokens'
  | 'agent.v2.turn.cost.calls'
  | 'agent.v2.turn.cost.est'
  | 'agent.v2.turn.warn.label'
  | 'agent.v2.turn.execute'
  | 'agent.v2.turn.cancel'
  | 'agent.v2.inspector.label'
  | 'agent.v2.inspector.empty'
  | 'agent.v2.inspector.skill'
  | 'agent.v2.inspector.planHash'
  | 'agent.v2.inspector.copied'
  | 'agent.v2.inspector.tokens'
  | 'agent.v2.inspector.calls'
  | 'agent.v2.inspector.estSec'
  | 'agent.v2.inspector.actions'
  | 'agent.v2.inspector.warnings'
  | 'agent.v2.skills.search.label'
  | 'agent.v2.skills.search.placeholder'
  | 'agent.v2.skills.tab.marketplace'
  | 'agent.v2.skills.tab.mySkills'
  | 'agent.v2.skills.newSkill'
  | 'agent.v2.skills.empty'
  | 'agent.v2.skills.card.edit'
  | 'agent.v2.skills.card.delete'
  | 'agent.v2.skills.editor.titleEdit'
  | 'agent.v2.skills.editor.titleNew'
  | 'agent.v2.skills.editor.field.name'
  | 'agent.v2.skills.editor.field.triggers'
  | 'agent.v2.skills.editor.field.triggersPlaceholder'
  | 'agent.v2.skills.editor.field.description'
  | 'agent.v2.skills.editor.field.tools'
  | 'agent.v2.skills.editor.field.toolsPlaceholder'
  | 'agent.v2.skills.editor.advanced'
  | 'agent.v2.skills.editor.field.planTemplate'
  | 'agent.v2.skills.editor.field.inputsSchema'
  | 'agent.v2.skills.editor.field.outputsSchema'
  | 'agent.v2.skills.editor.error.required'
  | 'agent.v2.skills.editor.error.invalidJson'
  | 'agent.v2.skills.editor.cancel'
  | 'agent.v2.skills.editor.save'
  | 'agent.v2.skills.import.label'
  | 'agent.v2.skills.import.mode.upsert'
  | 'agent.v2.skills.import.mode.insertOnly'
  | 'agent.v2.skills.import.dropHint'
  | 'agent.v2.skills.import.jsonLabel'
  | 'agent.v2.skills.import.jsonPlaceholder'
  | 'agent.v2.skills.import.submit'
  | 'agent.v2.skills.import.resultsLabel'
  | 'agent.v2.skills.import.error.readFailed'
  | 'agent.v2.skills.import.error.emptyJson'
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
    'header.menu.console': '控制台',
    'header.menu.logout': '退出登录',
    'header.menu.admin': '管理员',
    'header.menu.defaultUserName': '用户',
    'header.menu.defaultEmail': 'user@example.com',
    'console.title': '控制台',
    'console.nav.overview': '概览',
    'console.nav.users': '用户',
    'console.nav.storage': '存储',
    'console.nav.content': '内容审计',
    'console.nav.moderation': '违规处理',
    'console.nav.system': '系统状态',
    'console.nav.logs': '操作日志',
    'console.nav.notifications': '通知',
    'console.nav.rules': '注册规则',
    'sidebar.myFiles': '我的文件',
    'sidebar.shared': '共享',
    'sidebar.recycleBin': '回收站',
    'sidebar.starred': 'Starred',
    'sidebar.starredEmpty': '暂无收藏',
    'sidebar.workspaceTree': '工作区目录',
    'sidebar.storage': '存储',
    'sidebar.skills': '技能',
    'sidebar.agent': 'Agent',
    'sidebar.myFiles.uploadingAria': '我的文件有上传进行中',
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
    'settings.resetSuccess': '设置已重置。',
    'settings.appearance.theme.label': '主题',
    'settings.appearance.theme.description': '选择您喜欢的应用主题',
    'settings.appearance.theme.light': '浅色',
    'settings.appearance.theme.dark': '深色',
    'settings.appearance.compactMode.label': '紧凑模式',
    'settings.appearance.compactMode.description': '减少界面间距，显示更多内容',
    'settings.appearance.defaultFileView.label': '默认文件视图',
    'settings.appearance.defaultFileView.description': '选择文件列表的默认显示方式',
    'settings.appearance.defaultFileView.option.list': '列表视图',
    'settings.appearance.defaultFileView.option.grid': '网格视图',
    'settings.appearance.defaultFileView.option.tiles': '瓦片视图',
    'settings.appearance.showFileExtensions.label': '显示文件扩展名',
    'settings.appearance.showFileExtensions.description': '在文件名中显示文件扩展名',
    'settings.uploads.maxConcurrentUploads.label': '最大并发上传数',
    'settings.uploads.maxConcurrentUploads.description': '同时上传的最大文件数量',
    'settings.uploads.chunkSize.label': '分块大小',
    'settings.uploads.chunkSize.description': '大文件分块上传的块大小 (MB)',
    'settings.uploads.autoRetryFailedUploads.label': '自动重试失败的上传',
    'settings.uploads.autoRetryFailedUploads.description': '网络错误时自动重试上传',
    'settings.uploads.retryAttempts.label': '重试次数',
    'settings.uploads.retryAttempts.description': '上传失败时的最大重试次数',
    'settings.files.itemsPerPage.label': '每页显示项目数',
    'settings.files.itemsPerPage.description': '文件列表每页显示的项目数量',
    'settings.files.showHiddenFiles.label': '显示隐藏文件',
    'settings.files.showHiddenFiles.description': '显示以点(.)开头的隐藏文件',
    'settings.files.autoRefreshInterval.label': '自动刷新间隔',
    'settings.files.autoRefreshInterval.description': '文件列表自动刷新的时间间隔 (秒，0 表示禁用)',
    'settings.files.autoDeleteDays.label': '回收站自动清理',
    'settings.files.autoDeleteDays.description': '回收站中文件的自动删除天数',
    'settings.files.autoDeleteDays.option.7': '7 天',
    'settings.files.autoDeleteDays.option.14': '14 天',
    'settings.files.autoDeleteDays.option.30': '30 天',
    'settings.files.autoDeleteDays.option.60': '60 天',
    'settings.files.autoDeleteDays.option.90': '90 天',
    'settings.files.confirmDelete.label': '删除确认',
    'settings.files.confirmDelete.description': '删除文件时显示确认对话框',
    'settings.notifications.desktop.label': '桌面通知',
    'settings.notifications.desktop.description': '启用系统桌面通知',
    'settings.notifications.sound.label': '声音通知',
    'settings.notifications.sound.description': '操作完成时播放提示音',
    'settings.notifications.uploadComplete.label': '上传完成通知',
    'settings.notifications.uploadComplete.description': '文件上传完成时显示通知',
    'settings.notifications.error.label': '错误通知',
    'settings.notifications.error.description': '发生错误时显示通知',
    'settings.security.sessionTimeout.label': '会话超时时间',
    'settings.security.sessionTimeout.description': '自动登出的空闲时间 (分钟，0 表示禁用)',
    'settings.security.sessionTimeout.option.disabled': '禁用',
    'settings.security.sessionTimeout.option.30m': '30 分钟',
    'settings.security.sessionTimeout.option.1h': '1 小时',
    'settings.security.sessionTimeout.option.2h': '2 小时',
    'settings.security.sessionTimeout.option.4h': '4 小时',
    'settings.security.sessionTimeout.option.8h': '8 小时',
    'settings.security.requirePasswordForSensitiveActions.label': '敏感操作密码确认',
    'settings.security.requirePasswordForSensitiveActions.description': '执行删除、分享等敏感操作时要求密码确认',
    'settings.advanced.debugMode.label': '调试模式',
    'settings.advanced.debugMode.description': '启用详细的调试信息输出',
    'settings.advanced.cacheDuration.label': '缓存持续时间',
    'settings.advanced.cacheDuration.description': '本地缓存的保持时间 (小时)',
    'settings.advanced.cacheDuration.option.1h': '1 小时',
    'settings.advanced.cacheDuration.option.6h': '6 小时',
    'settings.advanced.cacheDuration.option.12h': '12 小时',
    'settings.advanced.cacheDuration.option.24h': '24 小时',
    'settings.advanced.cacheDuration.option.72h': '72 小时',
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
    'files.upload.action.cancel': '取消上传',
    'files.upload.action.resume': '继续上传',
    'files.upload.state.hashing': '计算校验中',
    'files.upload.state.uploading': '上传中',
    'files.upload.state.paused': '已暂停',
    'files.upload.state.canceling': '取消中',
    'files.upload.state.succeeded': '已完成',
    'files.upload.state.failed': '失败',
    'files.upload.state.canceled': '已取消',
    'files.upload.hint.sessionExpired': '上传会话已失效，请重新上传该文件。',
    'files.upload.hint.needReselect': '请重新选择同一个文件以继续断点续传。',
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
    'files.mediaOptimization.processing': '处理中',
    'files.mediaOptimization.ready': '已优化',
    'files.mediaOptimization.failedFallback': '优化失败，已回退原文件',
    'files.folder.loading': '加载中...',
    'files.folder.noSubfolders': '暂无子文件夹',
    'files.upload.toast.success': '已上传 {fileName}。',
    'files.upload.toast.failed': '上传 {fileName} 失败：{reason}',
    'files.upload.toast.unknownError': '未知错误',
    'files.star.toast.failed': '收藏操作失败：{reason}',
    'files.star.toast.unknownError': '未知错误',
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
    'sharing.table.links.regeneratePassword': '重置并查看密码',
    'sharing.table.links.delete': '删除',
    'sharing.batch.selected': '已选',
    'sharing.batch.acceptSelected': '接收所选',
    'sharing.batch.clear': '清除',
    'sharing.confirm.deleteLink.title': '删除共享链接',
    'sharing.confirm.deleteLink.message': '确定删除共享链接 {shareLink} 吗？',
    'sharing.confirm.deleteLink.confirm': '删除',
    'sharing.confirm.regeneratePassword.title': '重置并查看密码',
    'sharing.confirm.regeneratePassword.message': '确定重置共享链接 {shareLink} 的访问密码吗？旧密码将立即失效。',
    'sharing.confirm.regeneratePassword.confirm': '确认重置',
    'sharing.toast.linkDeleted': '共享链接已删除。',
    'sharing.toast.linkDeleteFailed': '删除共享链接失败。',
    'sharing.toast.linkCopied': '共享链接已复制。',
    'sharing.toast.passwordRegenerated': '已重置密码，请妥善保存新密码。',
    'sharing.toast.passwordRegenerateFailed': '重置密码失败，请重试。',
    'sharing.copyDialog.title': '复制共享链接',
    'sharing.copyDialog.message': '剪贴板不可用，请手动复制此链接：',
    'sharing.passwordDialog.title': '新共享密码',
    'sharing.passwordDialog.message': '请立即保存该密码，旧密码已失效：',
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
    'share.dialog.pendingApplyNotice': '所有改动将在点击“完成”后生效。',
    'share.dialog.confirmRevoke.title': '关闭公开链接',
    'share.dialog.confirmRevoke.message': '继续操作将导致当前共享链接失效，确认继续吗？',
    'share.dialog.confirmRevoke.confirm': '确认关闭',
    'share.dialog.generatedPassword.title': '已生成共享密码',
    'share.dialog.generatedPassword.message': '系统已自动生成密码，请先保存再关闭：',
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
    'files.preview.detail.unknownType': '未知类型',
    'files.preview.detail.download': '下载',
    'files.preview.detail.reload': '重新加载预览',
    'files.preview.detail.loading': '正在加载预览...',
    'files.preview.detail.notAvailable': '该文件类型暂不支持预览。',
    'files.preview.detail.placeholder': '选择一个文件以查看详情。',
    'files.preview.detail.loadFailed': '无法加载文件预览。',
    'files.preview.detail.downloadFailed': '无法下载该文件。',
    'files.preview.image.alt': '图片预览',
    'files.preview.pdf.prev': '上一页',
    'files.preview.pdf.next': '下一页',
    'files.preview.pdf.page': '第 {page} / {total} 页',
    'files.preview.pdf.fallbackMode': '使用浏览器 PDF 兜底渲染',
    'files.preview.pdf.fallbackNote': '当前环境不支持应用内 PDF 渲染。',
    'files.preview.pdf.retryRender': '重试渲染',
    'files.preview.pdf.openNewTab': '在新标签页打开',
    'files.preview.pdf.renderFailed': '无法渲染 PDF 预览。',
    'files.preview.video.loading': '正在加载预览...',
    'files.preview.video.loadFailed': '无法加载视频预览。',
    'files.preview.video.downloadFailed': '无法下载该文件。',
    'files.preview.video.mimeFallback': 'video',
    'agent.v2.layout.brand': '[ FILEFLASH · AGENT ]',
    'agent.v2.layout.tab.workspace': '工作台',
    'agent.v2.layout.tab.skills': '技能',
    'agent.v2.sessions.label': '会话',
    'agent.v2.sessions.new': '新建会话',
    'agent.v2.sessions.empty': '暂无会话。',
    'agent.v2.sessions.delete': '删除会话',
    'agent.v2.sessions.relative.justNow': '刚刚',
    'agent.v2.sessions.relative.minutes': '{value} 分钟前',
    'agent.v2.sessions.relative.hours': '{value} 小时前',
    'agent.v2.sessions.relative.days': '{value} 天前',
    'agent.v2.timeline.label': '时间线',
    'agent.v2.timeline.welcomeHint': '在下方输入任务以开始。',
    'agent.v2.timeline.hint.organize': '按日期把我的截图整理到不同文件夹',
    'agent.v2.timeline.hint.duplicates': '在我的照片库中查找重复项',
    'agent.v2.timeline.hint.tagInvoices': '为发票打标签并移动到 /finance',
    'agent.v2.input.placeholder': '描述一个任务，Shift+Enter 换行。',
    'agent.v2.input.send': '发送',
    'agent.v2.input.policy.planOnly': '仅生成计划',
    'agent.v2.input.policy.confirm': '确认执行',
    'agent.v2.input.policy.autopilot': '自动执行',
    'agent.v2.input.reasoning.adaptive': '自适应推理',
    'agent.v2.input.reasoning.low': '低推理',
    'agent.v2.input.reasoning.medium': '中推理',
    'agent.v2.input.reasoning.high': '高推理',
    'agent.v2.input.reasoning.xhigh': '超高推理',
    'agent.v2.input.reasoning.max': '最大推理',
    'agent.v2.turn.role': 'AGENT',
    'agent.v2.turn.status.pending': '等待中',
    'agent.v2.turn.status.running': '运行中',
    'agent.v2.turn.status.succeeded': '已完成',
    'agent.v2.turn.status.failed': '失败',
    'agent.v2.turn.status.canceled': '已取消',
    'agent.v2.turn.cost.label': '消耗',
    'agent.v2.turn.cost.tokens': 'tokens',
    'agent.v2.turn.cost.calls': '调用',
    'agent.v2.turn.cost.est': '预计',
    'agent.v2.turn.warn.label': '警告',
    'agent.v2.turn.execute': '执行',
    'agent.v2.turn.cancel': '取消',
    'agent.v2.inspector.label': '检视器',
    'agent.v2.inspector.empty': '选择一个回合以查看其计划详情。',
    'agent.v2.inspector.skill': 'SKILL',
    'agent.v2.inspector.planHash': 'PLAN HASH',
    'agent.v2.inspector.copied': '已复制',
    'agent.v2.inspector.tokens': 'TOKENS',
    'agent.v2.inspector.calls': 'CALLS',
    'agent.v2.inspector.estSec': '预计秒数',
    'agent.v2.inspector.actions': '步骤数',
    'agent.v2.inspector.warnings': '警告',
    'agent.v2.skills.search.label': '搜索',
    'agent.v2.skills.search.placeholder': '搜索技能...',
    'agent.v2.skills.tab.marketplace': '技能市场',
    'agent.v2.skills.tab.mySkills': '我的技能',
    'agent.v2.skills.newSkill': '新增技能',
    'agent.v2.skills.empty': '暂无技能。',
    'agent.v2.skills.card.edit': '编辑',
    'agent.v2.skills.card.delete': '删除',
    'agent.v2.skills.editor.titleEdit': '编辑 Skill',
    'agent.v2.skills.editor.titleNew': '新建 Skill',
    'agent.v2.skills.editor.field.name': '名称',
    'agent.v2.skills.editor.field.triggers': '触发词',
    'agent.v2.skills.editor.field.triggersPlaceholder': '整理, 分类',
    'agent.v2.skills.editor.field.description': '描述',
    'agent.v2.skills.editor.field.tools': '工具',
    'agent.v2.skills.editor.field.toolsPlaceholder': 'tool.a, tool.b',
    'agent.v2.skills.editor.advanced': '高级 JSON',
    'agent.v2.skills.editor.field.planTemplate': '计划模板',
    'agent.v2.skills.editor.field.inputsSchema': '输入 Schema',
    'agent.v2.skills.editor.field.outputsSchema': '输出 Schema',
    'agent.v2.skills.editor.error.required': '名称和描述为必填项。',
    'agent.v2.skills.editor.error.invalidJson': '{field} JSON 格式错误',
    'agent.v2.skills.editor.cancel': '取消',
    'agent.v2.skills.editor.save': '保存',
    'agent.v2.skills.import.label': '导入技能',
    'agent.v2.skills.import.mode.upsert': 'Upsert',
    'agent.v2.skills.import.mode.insertOnly': '仅新增',
    'agent.v2.skills.import.dropHint': '拖入 .json 文件或点击浏览',
    'agent.v2.skills.import.jsonLabel': 'JSON',
    'agent.v2.skills.import.jsonPlaceholder': '[{ "skillKey": "...", "name": "...", "description": "..." }]',
    'agent.v2.skills.import.submit': '导入',
    'agent.v2.skills.import.resultsLabel': '导入结果',
    'agent.v2.skills.import.error.readFailed': '读取文件失败。',
    'agent.v2.skills.import.error.emptyJson': '请先粘贴 JSON 或拖入文件。',
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
    'header.menu.console': 'Console',
    'header.menu.logout': 'Log out',
    'header.menu.admin': 'Admin',
    'header.menu.defaultUserName': 'User',
    'header.menu.defaultEmail': 'user@example.com',
    'console.title': 'Console',
    'console.nav.overview': 'Overview',
    'console.nav.users': 'Users',
    'console.nav.storage': 'Storage',
    'console.nav.content': 'Content Audit',
    'console.nav.moderation': 'Moderation',
    'console.nav.system': 'System',
    'console.nav.logs': 'Logs',
    'console.nav.notifications': 'Notifications',
    'console.nav.rules': 'Registration Rules',
    'sidebar.myFiles': 'My Files',
    'sidebar.shared': 'Shared',
    'sidebar.recycleBin': 'Recycle Bin',
    'sidebar.starred': 'Starred',
    'sidebar.starredEmpty': 'No starred items',
    'sidebar.workspaceTree': 'Workspace Tree',
    'sidebar.storage': 'Storage',
    'sidebar.skills': 'Skills',
    'sidebar.agent': 'Agent',
    'sidebar.myFiles.uploadingAria': 'My Files has uploads in progress',
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
    'settings.resetSuccess': 'Settings reset.',
    'settings.appearance.theme.label': 'Theme',
    'settings.appearance.theme.description': 'Choose your preferred app theme',
    'settings.appearance.theme.light': 'Light',
    'settings.appearance.theme.dark': 'Dark',
    'settings.appearance.compactMode.label': 'Compact Mode',
    'settings.appearance.compactMode.description': 'Reduce spacing to show more content',
    'settings.appearance.defaultFileView.label': 'Default File View',
    'settings.appearance.defaultFileView.description': 'Choose the default display mode for file lists',
    'settings.appearance.defaultFileView.option.list': 'List View',
    'settings.appearance.defaultFileView.option.grid': 'Grid View',
    'settings.appearance.defaultFileView.option.tiles': 'Tiles View',
    'settings.appearance.showFileExtensions.label': 'Show File Extensions',
    'settings.appearance.showFileExtensions.description': 'Display file extensions in filenames',
    'settings.uploads.maxConcurrentUploads.label': 'Max Concurrent Uploads',
    'settings.uploads.maxConcurrentUploads.description': 'Maximum number of files uploaded at the same time',
    'settings.uploads.chunkSize.label': 'Chunk Size',
    'settings.uploads.chunkSize.description': 'Chunk size for large file uploads (MB)',
    'settings.uploads.autoRetryFailedUploads.label': 'Auto Retry Failed Uploads',
    'settings.uploads.autoRetryFailedUploads.description': 'Automatically retry uploads on network errors',
    'settings.uploads.retryAttempts.label': 'Retry Attempts',
    'settings.uploads.retryAttempts.description': 'Maximum retry attempts when an upload fails',
    'settings.files.itemsPerPage.label': 'Items Per Page',
    'settings.files.itemsPerPage.description': 'Number of items displayed per page in file lists',
    'settings.files.showHiddenFiles.label': 'Show Hidden Files',
    'settings.files.showHiddenFiles.description': 'Display hidden files that start with a dot (.)',
    'settings.files.autoRefreshInterval.label': 'Auto Refresh Interval',
    'settings.files.autoRefreshInterval.description': 'Automatic refresh interval for file lists (seconds, 0 to disable)',
    'settings.files.autoDeleteDays.label': 'Trash Auto Cleanup',
    'settings.files.autoDeleteDays.description': 'Days before files in trash are automatically deleted',
    'settings.files.autoDeleteDays.option.7': '7 days',
    'settings.files.autoDeleteDays.option.14': '14 days',
    'settings.files.autoDeleteDays.option.30': '30 days',
    'settings.files.autoDeleteDays.option.60': '60 days',
    'settings.files.autoDeleteDays.option.90': '90 days',
    'settings.files.confirmDelete.label': 'Delete Confirmation',
    'settings.files.confirmDelete.description': 'Show a confirmation dialog before deleting files',
    'settings.notifications.desktop.label': 'Desktop Notifications',
    'settings.notifications.desktop.description': 'Enable system desktop notifications',
    'settings.notifications.sound.label': 'Sound Notifications',
    'settings.notifications.sound.description': 'Play a sound when actions complete',
    'settings.notifications.uploadComplete.label': 'Upload Complete Notifications',
    'settings.notifications.uploadComplete.description': 'Show notifications when uploads finish',
    'settings.notifications.error.label': 'Error Notifications',
    'settings.notifications.error.description': 'Show notifications when errors occur',
    'settings.security.sessionTimeout.label': 'Session Timeout',
    'settings.security.sessionTimeout.description': 'Idle time before automatic logout (minutes, 0 to disable)',
    'settings.security.sessionTimeout.option.disabled': 'Disabled',
    'settings.security.sessionTimeout.option.30m': '30 minutes',
    'settings.security.sessionTimeout.option.1h': '1 hour',
    'settings.security.sessionTimeout.option.2h': '2 hours',
    'settings.security.sessionTimeout.option.4h': '4 hours',
    'settings.security.sessionTimeout.option.8h': '8 hours',
    'settings.security.requirePasswordForSensitiveActions.label': 'Password Confirmation for Sensitive Actions',
    'settings.security.requirePasswordForSensitiveActions.description': 'Require password confirmation for sensitive actions like delete or share',
    'settings.advanced.debugMode.label': 'Debug Mode',
    'settings.advanced.debugMode.description': 'Enable detailed debug output',
    'settings.advanced.cacheDuration.label': 'Cache Duration',
    'settings.advanced.cacheDuration.description': 'How long local cache is retained (hours)',
    'settings.advanced.cacheDuration.option.1h': '1 hour',
    'settings.advanced.cacheDuration.option.6h': '6 hours',
    'settings.advanced.cacheDuration.option.12h': '12 hours',
    'settings.advanced.cacheDuration.option.24h': '24 hours',
    'settings.advanced.cacheDuration.option.72h': '72 hours',
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
    'files.upload.action.cancel': 'Cancel',
    'files.upload.action.resume': 'Resume',
    'files.upload.state.hashing': 'Hashing',
    'files.upload.state.uploading': 'Uploading',
    'files.upload.state.paused': 'Paused',
    'files.upload.state.canceling': 'Canceling',
    'files.upload.state.succeeded': 'Done',
    'files.upload.state.failed': 'Failed',
    'files.upload.state.canceled': 'Canceled',
    'files.upload.hint.sessionExpired': 'Upload session expired. Please upload this file again.',
    'files.upload.hint.needReselect': 'Please reselect the same file to resume upload.',
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
    'files.mediaOptimization.processing': 'Processing',
    'files.mediaOptimization.ready': 'Optimized',
    'files.mediaOptimization.failedFallback': 'Optimization failed, fallback to source',
    'files.folder.loading': 'Loading...',
    'files.folder.noSubfolders': 'No subfolders',
    'files.upload.toast.success': 'Uploaded {fileName}.',
    'files.upload.toast.failed': 'Upload of {fileName} failed: {reason}',
    'files.upload.toast.unknownError': 'Unknown error',
    'files.star.toast.failed': 'Failed to update star status: {reason}',
    'files.star.toast.unknownError': 'Unknown error',
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
    'sharing.table.links.regeneratePassword': 'Reset & Show Password',
    'sharing.table.links.delete': 'Delete',
    'sharing.batch.selected': 'SELECTED',
    'sharing.batch.acceptSelected': 'Accept Selected',
    'sharing.batch.clear': 'Clear',
    'sharing.confirm.deleteLink.title': 'Delete Share Link',
    'sharing.confirm.deleteLink.message': 'Delete share link {shareLink}?',
    'sharing.confirm.deleteLink.confirm': 'Delete',
    'sharing.confirm.regeneratePassword.title': 'Reset and Show Password',
    'sharing.confirm.regeneratePassword.message': 'Reset the password for share link {shareLink}? The old password will be invalid immediately.',
    'sharing.confirm.regeneratePassword.confirm': 'Reset Password',
    'sharing.toast.linkDeleted': 'Share link deleted.',
    'sharing.toast.linkDeleteFailed': 'Failed to delete share link.',
    'sharing.toast.linkCopied': 'Share link copied.',
    'sharing.toast.passwordRegenerated': 'Password reset successfully. Save the new password now.',
    'sharing.toast.passwordRegenerateFailed': 'Failed to reset password.',
    'sharing.copyDialog.title': 'Copy Share Link',
    'sharing.copyDialog.message': 'Clipboard is unavailable. Copy this link manually:',
    'sharing.passwordDialog.title': 'New Share Password',
    'sharing.passwordDialog.message': 'Save this password now. The old password is no longer valid:',
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
    'share.dialog.pendingApplyNotice': 'All changes will take effect only after you click "Done".',
    'share.dialog.confirmRevoke.title': 'Disable Public Link',
    'share.dialog.confirmRevoke.message': 'Continuing will invalidate this share link. Do you want to proceed?',
    'share.dialog.confirmRevoke.confirm': 'Disable Link',
    'share.dialog.generatedPassword.title': 'Generated Share Password',
    'share.dialog.generatedPassword.message': 'A password was generated automatically. Save it before closing:',
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
    'files.preview.detail.unknownType': 'Unknown type',
    'files.preview.detail.download': 'Download',
    'files.preview.detail.reload': 'Reload Preview',
    'files.preview.detail.loading': 'Loading preview...',
    'files.preview.detail.notAvailable': 'Preview is not available for this file type.',
    'files.preview.detail.placeholder': 'Select a file to preview details.',
    'files.preview.detail.loadFailed': 'Unable to load file preview.',
    'files.preview.detail.downloadFailed': 'Unable to download this file.',
    'files.preview.image.alt': 'Image preview',
    'files.preview.pdf.prev': 'Prev',
    'files.preview.pdf.next': 'Next',
    'files.preview.pdf.page': 'Page {page} / {total}',
    'files.preview.pdf.fallbackMode': 'Browser PDF fallback mode',
    'files.preview.pdf.fallbackNote': 'In-app PDF rendering is unavailable in this environment.',
    'files.preview.pdf.retryRender': 'Retry render',
    'files.preview.pdf.openNewTab': 'Open in new tab',
    'files.preview.pdf.renderFailed': 'Unable to render PDF preview.',
    'files.preview.video.loading': 'Loading preview...',
    'files.preview.video.loadFailed': 'Unable to load video preview.',
    'files.preview.video.downloadFailed': 'Unable to download this file.',
    'files.preview.video.mimeFallback': 'video',
    'agent.v2.layout.brand': '[ FILEFLASH · AGENT ]',
    'agent.v2.layout.tab.workspace': 'WORKSPACE',
    'agent.v2.layout.tab.skills': 'SKILLS',
    'agent.v2.sessions.label': 'SESSIONS',
    'agent.v2.sessions.new': 'New session',
    'agent.v2.sessions.empty': 'No sessions yet.',
    'agent.v2.sessions.delete': 'Delete session',
    'agent.v2.sessions.relative.justNow': 'just now',
    'agent.v2.sessions.relative.minutes': '{value}m',
    'agent.v2.sessions.relative.hours': '{value}h',
    'agent.v2.sessions.relative.days': '{value}d',
    'agent.v2.timeline.label': 'TIMELINE',
    'agent.v2.timeline.welcomeHint': 'Type a task below to get started.',
    'agent.v2.timeline.hint.organize': 'Organize my screenshots into folders by date',
    'agent.v2.timeline.hint.duplicates': 'Find duplicates across my photo library',
    'agent.v2.timeline.hint.tagInvoices': 'Tag invoices and move them under /finance',
    'agent.v2.input.placeholder': 'Describe a task. Shift+Enter for newline.',
    'agent.v2.input.send': 'Send',
    'agent.v2.input.policy.planOnly': 'PLAN ONLY',
    'agent.v2.input.policy.confirm': 'CONFIRM',
    'agent.v2.input.policy.autopilot': 'AUTOPILOT',
    'agent.v2.input.reasoning.adaptive': 'ADAPTIVE',
    'agent.v2.input.reasoning.low': 'LOW',
    'agent.v2.input.reasoning.medium': 'MEDIUM',
    'agent.v2.input.reasoning.high': 'HIGH',
    'agent.v2.input.reasoning.xhigh': 'XHIGH',
    'agent.v2.input.reasoning.max': 'MAX',
    'agent.v2.turn.role': 'AGENT',
    'agent.v2.turn.status.pending': 'pending',
    'agent.v2.turn.status.running': 'running',
    'agent.v2.turn.status.succeeded': 'succeeded',
    'agent.v2.turn.status.failed': 'failed',
    'agent.v2.turn.status.canceled': 'canceled',
    'agent.v2.turn.cost.label': 'COST',
    'agent.v2.turn.cost.tokens': 'tokens',
    'agent.v2.turn.cost.calls': 'calls',
    'agent.v2.turn.cost.est': 'est',
    'agent.v2.turn.warn.label': 'WARN',
    'agent.v2.turn.execute': 'Execute',
    'agent.v2.turn.cancel': 'Cancel',
    'agent.v2.inspector.label': 'INSPECTOR',
    'agent.v2.inspector.empty': 'Select a turn to inspect its plan.',
    'agent.v2.inspector.skill': 'SKILL',
    'agent.v2.inspector.planHash': 'PLAN HASH',
    'agent.v2.inspector.copied': 'COPIED',
    'agent.v2.inspector.tokens': 'TOKENS',
    'agent.v2.inspector.calls': 'CALLS',
    'agent.v2.inspector.estSec': 'EST SEC',
    'agent.v2.inspector.actions': 'ACTIONS',
    'agent.v2.inspector.warnings': 'WARNINGS',
    'agent.v2.skills.search.label': 'SEARCH',
    'agent.v2.skills.search.placeholder': 'Search skills...',
    'agent.v2.skills.tab.marketplace': 'MARKETPLACE',
    'agent.v2.skills.tab.mySkills': 'MY SKILLS',
    'agent.v2.skills.newSkill': 'New Skill',
    'agent.v2.skills.empty': 'No skills here yet.',
    'agent.v2.skills.card.edit': 'Edit',
    'agent.v2.skills.card.delete': 'Delete',
    'agent.v2.skills.editor.titleEdit': 'Edit Skill',
    'agent.v2.skills.editor.titleNew': 'New Skill',
    'agent.v2.skills.editor.field.name': 'NAME',
    'agent.v2.skills.editor.field.triggers': 'TRIGGERS',
    'agent.v2.skills.editor.field.triggersPlaceholder': 'organize, classify',
    'agent.v2.skills.editor.field.description': 'DESCRIPTION',
    'agent.v2.skills.editor.field.tools': 'TOOLS',
    'agent.v2.skills.editor.field.toolsPlaceholder': 'tool.a, tool.b',
    'agent.v2.skills.editor.advanced': 'ADVANCED JSON',
    'agent.v2.skills.editor.field.planTemplate': 'PLAN TEMPLATE',
    'agent.v2.skills.editor.field.inputsSchema': 'INPUTS SCHEMA',
    'agent.v2.skills.editor.field.outputsSchema': 'OUTPUTS SCHEMA',
    'agent.v2.skills.editor.error.required': 'Name and description are required.',
    'agent.v2.skills.editor.error.invalidJson': '{field} JSON invalid',
    'agent.v2.skills.editor.cancel': 'Cancel',
    'agent.v2.skills.editor.save': 'Save',
    'agent.v2.skills.import.label': 'IMPORT SKILLS',
    'agent.v2.skills.import.mode.upsert': 'UPSERT',
    'agent.v2.skills.import.mode.insertOnly': 'INSERT ONLY',
    'agent.v2.skills.import.dropHint': 'Drop a .json file or click to browse',
    'agent.v2.skills.import.jsonLabel': 'JSON',
    'agent.v2.skills.import.jsonPlaceholder': '[{ "skillKey": "...", "name": "...", "description": "..." }]',
    'agent.v2.skills.import.submit': 'Import',
    'agent.v2.skills.import.resultsLabel': 'RESULTS',
    'agent.v2.skills.import.error.readFailed': 'Failed to read file.',
    'agent.v2.skills.import.error.emptyJson': 'Paste JSON or drop a file first.',
    'footer.termsOfService': 'Terms of Service',
    'footer.privacyPolicy': 'Privacy Policy',
  },
};
