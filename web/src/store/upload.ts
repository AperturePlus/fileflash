import { computed, ref, watch } from 'vue';
import { defineStore } from 'pinia';
import { cancelUploadSession, getRecoverableUploads } from '../api/file';
import type { UploadRecoverableSession } from '../types/file';
import { useFileStore } from './file';
import { useLocaleStore } from './locale';
import { useSettingsStore } from './settings';
import { eventBus } from '../utils/eventBus';
import { ui } from '../utils/ui';
import { completeUploadSession, isUploadCanceledError, uploadFile, type UploadProgressData } from '../utils/uploader';

export type UploadTaskStatus = 'hashing' | 'uploading' | 'paused' | 'succeeded' | 'failed' | 'canceled';

export interface UploadTask {
  id: string;
  name: string;
  parentId: string;
  uploadId: string | null;
  fileHash: string | null;
  mimeType: string | null;
  status: UploadTaskStatus;
  progress: UploadProgressData;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
  isCanceling: boolean;
}

interface PersistedUploadTask {
  id: string;
  name: string;
  parentId: string;
  uploadId: string | null;
  fileHash: string | null;
  mimeType: string | null;
  status: UploadTaskStatus;
  progress: UploadProgressData;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

const UPLOAD_TASKS_STORAGE_KEY = 'fileflash-upload-tasks-v1';
const TERMINAL_TASK_STATUSES: UploadTaskStatus[] = ['succeeded', 'failed', 'canceled'];
const PERSISTABLE_STATUSES: UploadTaskStatus[] = ['uploading', 'paused'];

function calcPercentage(uploadedSize: number, totalSize: number): number {
  if (totalSize <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((uploadedSize / totalSize) * 100)));
}

function hasWindow(): boolean {
  return typeof window !== 'undefined' && typeof localStorage !== 'undefined';
}

export const useUploadStore = defineStore('upload', () => {
  const fileStore = useFileStore();
  const localeStore = useLocaleStore();
  const settingsStore = useSettingsStore();

  const tasks = ref<UploadTask[]>([]);
  const controllers = new Map<string, AbortController>();
  const cleanupTimers = new Map<string, number>();
  let hasBootstrappedRecovery = false;
  let hasBeforeUnloadGuard = false;
  const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
    event.preventDefault();
    event.returnValue = '';
  };

  const activeUploadingCount = computed(() =>
    tasks.value.filter((task) =>
      task.status === 'hashing' || task.status === 'uploading' || task.isCanceling).length,
  );

  const formatMessage = (
    key: 'files.upload.toast.success' | 'files.upload.toast.failed',
    vars: Record<string, string>,
  ) => {
    let message = localeStore.t(key);
    for (const [varName, value] of Object.entries(vars)) {
      message = message.replace(`{${varName}}`, value);
    }
    return message;
  };

  const findTaskById = (taskId: string) => tasks.value.find((task) => task.id === taskId) || null;

  const buildPausedTask = (task: PersistedUploadTask): UploadTask => {
    const totalSize = Math.max(0, Number(task.progress?.totalSize || 0));
    const uploadedSize = Math.min(totalSize, Math.max(0, Number(task.progress?.uploadedSize || 0)));
    return {
      id: String(task.id),
      name: String(task.name),
      parentId: String(task.parentId || 'root'),
      uploadId: task.uploadId ? String(task.uploadId) : null,
      fileHash: task.fileHash ? String(task.fileHash) : null,
      mimeType: task.mimeType ? String(task.mimeType) : null,
      status: 'paused',
      progress: {
        percentage: calcPercentage(uploadedSize, totalSize),
        uploadedSize,
        totalSize,
      },
      errorMessage: localeStore.t('files.upload.hint.needReselect'),
      createdAt: String(task.createdAt || new Date().toISOString()),
      updatedAt: String(task.updatedAt || new Date().toISOString()),
      isCanceling: false,
    };
  };

  const loadPersistedTasks = (): UploadTask[] => {
    if (!hasWindow()) return [];
    try {
      const raw = localStorage.getItem(UPLOAD_TASKS_STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw) as PersistedUploadTask[];
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter((item) => item && typeof item === 'object')
        .filter((item) => item.uploadId && PERSISTABLE_STATUSES.includes(item.status))
        .map(buildPausedTask);
    } catch {
      return [];
    }
  };

  const savePersistedTasks = () => {
    if (!hasWindow()) return;
    const payload: PersistedUploadTask[] = tasks.value
      .filter((task) => task.uploadId && PERSISTABLE_STATUSES.includes(task.status))
      .map((task) => ({
        id: task.id,
        name: task.name,
        parentId: task.parentId,
        uploadId: task.uploadId,
        fileHash: task.fileHash,
        mimeType: task.mimeType,
        status: task.status,
        progress: task.progress,
        errorMessage: task.errorMessage,
        createdAt: task.createdAt,
        updatedAt: task.updatedAt,
      }));
    if (!payload.length) {
      localStorage.removeItem(UPLOAD_TASKS_STORAGE_KEY);
      return;
    }
    localStorage.setItem(UPLOAD_TASKS_STORAGE_KEY, JSON.stringify(payload));
  };

  const syncBeforeUnloadGuard = (count: number) => {
    if (!hasWindow()) return;
    if (count > 0 && !hasBeforeUnloadGuard) {
      window.addEventListener('beforeunload', beforeUnloadHandler);
      hasBeforeUnloadGuard = true;
      return;
    }
    if (count <= 0 && hasBeforeUnloadGuard) {
      window.removeEventListener('beforeunload', beforeUnloadHandler);
      hasBeforeUnloadGuard = false;
    }
  };

  watch(tasks, savePersistedTasks, { deep: true });
  watch(activeUploadingCount, syncBeforeUnloadGuard, { immediate: true });

  const removeTask = (taskId: string) => {
    const timer = cleanupTimers.get(taskId);
    if (timer !== undefined) {
      window.clearTimeout(timer);
      cleanupTimers.delete(taskId);
    }
    controllers.delete(taskId);
    tasks.value = tasks.value.filter((task) => task.id !== taskId);
  };

  const scheduleTaskRemoval = (taskId: string, delayMs = 5000) => {
    const timer = cleanupTimers.get(taskId);
    if (timer !== undefined) {
      window.clearTimeout(timer);
    }
    const timeout = window.setTimeout(() => {
      cleanupTimers.delete(taskId);
      removeTask(taskId);
    }, delayMs);
    cleanupTimers.set(taskId, timeout);
  };

  const updateTask = (taskId: string, updater: (task: UploadTask) => void) => {
    const task = findTaskById(taskId);
    if (!task) return;
    updater(task);
    task.updatedAt = new Date().toISOString();
  };

  const markTaskTerminal = (taskId: string, nextStatus: UploadTaskStatus, errorMessage: string | null = null) => {
    if (!TERMINAL_TASK_STATUSES.includes(nextStatus)) return;
    updateTask(taskId, (task) => {
      task.status = nextStatus;
      task.errorMessage = errorMessage;
      task.isCanceling = false;
    });
    controllers.delete(taskId);
    scheduleTaskRemoval(taskId);
  };

  const attachUploadedFile = (payload: {
    fileId: string;
    fileName: string;
    fileSize: number;
    mimeType: string;
    folderId: string;
    createdAt: string;
  }) => {
    if (fileStore.currentFolderId !== payload.folderId) {
      return;
    }
    const fileItem = {
      itemType: 'file' as const,
      id: payload.fileId,
      name: payload.fileName,
      size: payload.fileSize,
      mimeType: payload.mimeType,
      ownerName: localeStore.t('files.owner.you'),
      updatedAt: payload.createdAt,
      createdAt: payload.createdAt,
      folderId: payload.folderId,
      permission: 'owner' as const,
    };
    fileStore.items.unshift(fileItem);
  };

  async function runUploadTask(
    taskId: string,
    file: File,
    parentId: string,
    controller: AbortController,
    mode: 'new' | 'resume',
  ): Promise<void> {
    try {
      const newFile = await uploadFile({
        file,
        parentId,
        chunkSize: Math.max(1, settingsStore.settings.chunkSize) * 1024 * 1024,
        concurrency: Math.max(1, settingsStore.settings.maxConcurrentUploads),
        maxRetries: settingsStore.settings.autoRetryFailedUploads
          ? Math.max(1, settingsStore.settings.retryAttempts)
          : 1,
        signal: controller.signal,
        onFileHashed: (fileHash) => {
          updateTask(taskId, (task) => {
            task.fileHash = fileHash;
            task.mimeType = file.type || task.mimeType;
          });
        },
        onUploadId: (uploadId) => {
          updateTask(taskId, (task) => {
            task.uploadId = uploadId;
            task.status = 'uploading';
            task.errorMessage = null;
          });
        },
        onUploadProgress: (progressData) => {
          updateTask(taskId, (task) => {
            task.status = 'uploading';
            task.progress = progressData;
          });
        },
      });

      updateTask(taskId, (task) => {
        task.status = 'succeeded';
        task.progress = {
          percentage: 100,
          uploadedSize: task.progress.totalSize,
          totalSize: task.progress.totalSize,
        };
        task.errorMessage = null;
      });

      attachUploadedFile(newFile);

      if (settingsStore.settings.uploadCompleteNotification) {
        ui.toast({
          type: 'success',
          message: formatMessage('files.upload.toast.success', { fileName: `"${file.name}"` }),
        });
      }

      eventBus.emit('refresh-file-tree');
      markTaskTerminal(taskId, 'succeeded');
    } catch (error) {
      if (isUploadCanceledError(error)) {
        markTaskTerminal(taskId, 'canceled');
        return;
      }
      const reason = error instanceof Error && error.message
        ? error.message
        : localeStore.t('files.upload.toast.unknownError');
      if (mode === 'resume') {
        updateTask(taskId, (task) => {
          task.status = 'paused';
          task.errorMessage = reason;
          task.isCanceling = false;
        });
        controllers.delete(taskId);
        return;
      }
      ui.toast({
        type: 'error',
        message: formatMessage('files.upload.toast.failed', { fileName: file.name, reason }),
      });
      markTaskTerminal(taskId, 'failed', reason);
    }
  }

  const applyRecoverableSession = (task: UploadTask, session: UploadRecoverableSession) => {
    const totalSize = Math.max(0, Number(session.fileSize || 0));
    const uploadedSize = Math.min(totalSize, Math.max(0, Number(session.uploadedBytes || 0)));
    task.name = session.fileName;
    task.parentId = session.parentId || task.parentId || 'root';
    task.uploadId = session.uploadId;
    task.fileHash = session.fileHash;
    task.mimeType = session.mimeType;
    task.progress = {
      percentage: calcPercentage(uploadedSize, totalSize),
      uploadedSize,
      totalSize,
    };
    task.status = 'paused';
    task.isCanceling = false;
    task.errorMessage = localeStore.t('files.upload.hint.needReselect');
    task.updatedAt = session.updatedAt || new Date().toISOString();
  };

  const tryAutoMergeTask = async (taskId: string): Promise<void> => {
    const task = findTaskById(taskId);
    if (!task || !task.uploadId || !task.fileHash || !task.mimeType) {
      return;
    }
    if (task.progress.totalSize <= 0 || task.progress.uploadedSize < task.progress.totalSize) {
      return;
    }
    try {
      const merged = await completeUploadSession({
        uploadId: task.uploadId,
        fileHash: task.fileHash,
        fileName: task.name,
        mimeType: task.mimeType,
        parentId: task.parentId,
      });
      updateTask(taskId, (current) => {
        current.status = 'succeeded';
        current.progress = {
          percentage: 100,
          uploadedSize: current.progress.totalSize,
          totalSize: current.progress.totalSize,
        };
        current.errorMessage = null;
      });
      attachUploadedFile(merged);
      eventBus.emit('refresh-file-tree');
      markTaskTerminal(taskId, 'succeeded');
    } catch (error) {
      const reason = error instanceof Error && error.message
        ? error.message
        : localeStore.t('files.upload.toast.unknownError');
      updateTask(taskId, (current) => {
        current.status = 'paused';
        current.errorMessage = reason;
        current.isCanceling = false;
      });
    }
  };

  async function syncRecoverableTasks(): Promise<void> {
    let sessions: UploadRecoverableSession[] = [];
    try {
      sessions = await getRecoverableUploads();
    } catch (error) {
      console.warn('Failed to fetch recoverable upload sessions:', error);
      return;
    }
    const sessionByUploadId = new Map(sessions.map((session) => [session.uploadId, session]));

    for (const task of tasks.value) {
      if (!task.uploadId || TERMINAL_TASK_STATUSES.includes(task.status)) {
        continue;
      }
      const matched = sessionByUploadId.get(task.uploadId);
      if (!matched) {
        updateTask(task.id, (current) => {
          current.status = 'paused';
          current.isCanceling = false;
          current.errorMessage = localeStore.t('files.upload.hint.sessionExpired');
        });
        continue;
      }
      applyRecoverableSession(task, matched);
      sessionByUploadId.delete(task.uploadId);
    }

    for (const session of sessionByUploadId.values()) {
      const totalSize = Math.max(0, Number(session.fileSize || 0));
      const uploadedSize = Math.min(totalSize, Math.max(0, Number(session.uploadedBytes || 0)));
      tasks.value.push({
        id: `recovered-${session.uploadId}`,
        name: session.fileName,
        parentId: session.parentId || 'root',
        uploadId: session.uploadId,
        fileHash: session.fileHash,
        mimeType: session.mimeType,
        status: 'paused',
        progress: {
          percentage: calcPercentage(uploadedSize, totalSize),
          uploadedSize,
          totalSize,
        },
        errorMessage: localeStore.t('files.upload.hint.needReselect'),
        createdAt: session.updatedAt || new Date().toISOString(),
        updatedAt: session.updatedAt || new Date().toISOString(),
        isCanceling: false,
      });
    }

    const autoMergeCandidates = tasks.value
      .filter((task) => task.status === 'paused' && !!task.uploadId)
      .filter((task) => task.progress.totalSize > 0 && task.progress.uploadedSize >= task.progress.totalSize)
      .map((task) => task.id);
    for (const taskId of autoMergeCandidates) {
      // Keep sequential order so UI feedback remains deterministic.
      // eslint-disable-next-line no-await-in-loop
      await tryAutoMergeTask(taskId);
    }
  }

  async function bootstrapRecovery(): Promise<void> {
    if (hasBootstrappedRecovery) return;
    hasBootstrappedRecovery = true;
    if (!tasks.value.length) {
      tasks.value = loadPersistedTasks();
    }
    await syncRecoverableTasks();
  }

  async function startUpload(file: File, parentId: string): Promise<string> {
    const taskId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const now = new Date().toISOString();
    const controller = new AbortController();

    const task: UploadTask = {
      id: taskId,
      name: file.name,
      parentId,
      uploadId: null,
      fileHash: null,
      mimeType: file.type || null,
      status: 'hashing',
      progress: {
        percentage: 0,
        uploadedSize: 0,
        totalSize: file.size,
      },
      errorMessage: null,
      createdAt: now,
      updatedAt: now,
      isCanceling: false,
    };

    tasks.value.push(task);
    controllers.set(taskId, controller);

    void runUploadTask(taskId, file, parentId, controller, 'new');
    return taskId;
  }

  async function resumeTask(taskId: string, file: File): Promise<void> {
    const task = findTaskById(taskId);
    if (!task) return;
    if (TERMINAL_TASK_STATUSES.includes(task.status) || task.isCanceling) return;
    if (file.name !== task.name || file.size !== task.progress.totalSize) {
      const message = localeStore.t('files.upload.hint.needReselect');
      updateTask(taskId, (current) => {
        current.status = 'paused';
        current.errorMessage = message;
      });
      return;
    }

    const controller = new AbortController();
    controllers.set(taskId, controller);
    updateTask(taskId, (current) => {
      current.status = 'hashing';
      current.errorMessage = null;
      current.isCanceling = false;
      current.mimeType = file.type || current.mimeType;
    });

    void runUploadTask(taskId, file, task.parentId, controller, 'resume');
  }

  async function cancelTask(taskId: string): Promise<void> {
    const task = findTaskById(taskId);
    if (!task) return;
    if (TERMINAL_TASK_STATUSES.includes(task.status)) return;

    updateTask(taskId, (current) => {
      current.isCanceling = true;
      current.status = 'canceled';
      current.errorMessage = null;
    });

    const controller = controllers.get(taskId);
    if (controller) {
      controllers.delete(taskId);
      controller.abort();
    }

    if (task.uploadId) {
      try {
        await cancelUploadSession(task.uploadId);
      } catch (error) {
        console.warn('Failed to cancel upload session on server:', error);
      }
    }

    markTaskTerminal(taskId, 'canceled');
  }

  return {
    tasks,
    activeUploadingCount,
    startUpload,
    resumeTask,
    cancelTask,
    removeTask,
    bootstrapRecovery,
    syncRecoverableTasks,
  };
});
