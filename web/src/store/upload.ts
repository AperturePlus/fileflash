import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { cancelUploadSession } from '../api/file';
import { useFileStore } from './file';
import { useLocaleStore } from './locale';
import { useSettingsStore } from './settings';
import { eventBus } from '../utils/eventBus';
import { ui } from '../utils/ui';
import { isUploadCanceledError, uploadFile, type UploadProgressData } from '../utils/uploader';

export type UploadTaskStatus = 'hashing' | 'uploading' | 'succeeded' | 'failed' | 'canceled';

export interface UploadTask {
  id: string;
  name: string;
  parentId: string;
  uploadId: string | null;
  status: UploadTaskStatus;
  progress: UploadProgressData;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
  isCanceling: boolean;
}

const TERMINAL_TASK_STATUSES: UploadTaskStatus[] = ['succeeded', 'failed', 'canceled'];

export const useUploadStore = defineStore('upload', () => {
  const fileStore = useFileStore();
  const localeStore = useLocaleStore();
  const settingsStore = useSettingsStore();

  const tasks = ref<UploadTask[]>([]);
  const controllers = new Map<string, AbortController>();
  const cleanupTimers = new Map<string, number>();

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

  async function startUpload(file: File, parentId: string): Promise<string> {
    const taskId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const now = new Date().toISOString();
    const controller = new AbortController();

    const task: UploadTask = {
      id: taskId,
      name: file.name,
      parentId,
      uploadId: null,
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

    void runUploadTask(taskId, file, parentId, controller);
    return taskId;
  }

  async function runUploadTask(
    taskId: string,
    file: File,
    parentId: string,
    controller: AbortController,
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
      });

      if (fileStore.currentFolderId === newFile.folderId) {
        const fileItem = {
          itemType: 'file' as const,
          id: newFile.fileId,
          name: newFile.fileName,
          size: newFile.fileSize,
          mimeType: newFile.mimeType,
          ownerName: localeStore.t('files.owner.you'),
          updatedAt: newFile.createdAt,
          createdAt: newFile.createdAt,
          folderId: newFile.folderId,
          permission: 'owner' as const,
        };
        fileStore.items.unshift(fileItem);
      }

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
      ui.toast({
        type: 'error',
        message: formatMessage('files.upload.toast.failed', { fileName: file.name, reason }),
      });
      markTaskTerminal(taskId, 'failed', reason);
    }
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
    cancelTask,
    removeTask,
  };
});
