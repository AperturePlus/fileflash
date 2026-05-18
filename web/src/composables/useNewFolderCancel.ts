import type { Ref } from 'vue';

export interface UseNewFolderCancelOptions {
  renameInputValue: Ref<string>;
  onCancel: () => void;
}

export function useNewFolderCancel(options: UseNewFolderCancelOptions) {
  let listener: ((ev: PointerEvent) => void) | null = null;

  const install = (tempId: string) => {
    uninstall();
    const onPointerDown = (ev: PointerEvent) => {
      const target = ev.target as Element | null;
      if (!target) return;
      const guard = `[data-temp-folder-row="${tempId}"], [data-ui-toast], [data-dropdown-menu]`;
      if (target.closest(guard)) return;
      if (options.renameInputValue.value.trim() !== '') return;
      uninstall();
      options.onCancel();
    };
    listener = onPointerDown;
    document.addEventListener('pointerdown', onPointerDown, { capture: true });
  };

  const uninstall = () => {
    if (!listener) return;
    document.removeEventListener('pointerdown', listener, { capture: true });
    listener = null;
  };

  return { install, uninstall };
}
