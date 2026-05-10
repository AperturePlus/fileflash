import { reactive } from 'vue';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

export interface PromptOptions extends ConfirmOptions {
  placeholder?: string;
  defaultValue?: string;
  readonly?: boolean;
  confirmText?: string;
  cancelText?: string;
}

export interface ToastOptions {
  message: string;
  type?: ToastType;
  duration?: number;
}

export interface CopyTextOptions {
  title?: string;
  message?: string;
  text: string;
}

interface ActiveConfirm extends ConfirmOptions {
  resolve: (value: boolean) => void;
}

interface ActivePrompt extends PromptOptions {
  resolve: (value: string | null) => void;
}

interface ActiveToast {
  id: number;
  message: string;
  type: ToastType;
}

let toastId = 1;

export const uiState = reactive<{
  confirm: ActiveConfirm | null;
  prompt: ActivePrompt | null;
  toasts: ActiveToast[];
}>({
  confirm: null,
  prompt: null,
  toasts: [],
});

export const ui = {
  confirm(options: ConfirmOptions | string): Promise<boolean> {
    const normalized = typeof options === 'string' ? { message: options } : options;
    return new Promise<boolean>((resolve) => {
      uiState.confirm = {
        title: normalized.title || 'Confirm Action',
        message: normalized.message,
        confirmText: normalized.confirmText || 'Confirm',
        cancelText: normalized.cancelText || 'Cancel',
        danger: Boolean(normalized.danger),
        resolve,
      };
    });
  },

  promptText(options: PromptOptions | string): Promise<string | null> {
    const normalized = typeof options === 'string' ? { message: options } : options;
    return new Promise<string | null>((resolve) => {
      uiState.prompt = {
        title: normalized.title || 'Input Required',
        message: normalized.message,
        placeholder: normalized.placeholder || '',
        defaultValue: normalized.defaultValue || '',
        readonly: Boolean(normalized.readonly),
        confirmText: normalized.confirmText || 'Confirm',
        cancelText: normalized.cancelText || 'Cancel',
        danger: Boolean(normalized.danger),
        resolve,
      };
    });
  },

  async copyText(options: CopyTextOptions | string): Promise<void> {
    const normalized =
      typeof options === 'string'
        ? { text: options }
        : options;
    await this.promptText({
      title: normalized.title || 'Copy Text',
      message: normalized.message || 'Clipboard is unavailable. Copy text manually:',
      defaultValue: normalized.text,
      readonly: true,
      confirmText: 'Close',
      cancelText: 'Close',
    });
  },

  toast(options: ToastOptions | string): void {
    const normalized = typeof options === 'string' ? { message: options } : options;
    const toast: ActiveToast = {
      id: toastId,
      message: normalized.message,
      type: normalized.type || 'info',
    };
    toastId += 1;
    uiState.toasts.push(toast);

    const duration = Math.max(1200, normalized.duration || 2600);
    window.setTimeout(() => {
      const idx = uiState.toasts.findIndex((item) => item.id === toast.id);
      if (idx !== -1) {
        uiState.toasts.splice(idx, 1);
      }
    }, duration);
  },

  resolveConfirm(value: boolean): void {
    const active = uiState.confirm;
    if (!active) return;
    uiState.confirm = null;
    active.resolve(value);
  },

  resolvePrompt(value: string | null): void {
    const active = uiState.prompt;
    if (!active) return;
    uiState.prompt = null;
    active.resolve(value);
  },

  dismissToast(id: number): void {
    const idx = uiState.toasts.findIndex((item) => item.id === id);
    if (idx !== -1) {
      uiState.toasts.splice(idx, 1);
    }
  },
};
