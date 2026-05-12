import { reactive, onUnmounted } from 'vue';

type ColKey = 'name' | 'size' | 'time';

const DEFAULT_WIDTHS: Record<ColKey, number> = {
  name: 360,
  size: 120,
  time: 200,
};
const MIN: Record<ColKey, number> = { name: 120, size: 60, time: 120 };
const MAX: Record<ColKey, number> = { name: 800, size: 200, time: 280 };

const clamp = (v: number, lo: number, hi: number) =>
  Math.min(hi, Math.max(lo, v));

export function useColumnResize() {
  const colWidths = reactive({ ...DEFAULT_WIDTHS });

  let activeCol: ColKey | null = null;
  let startX = 0;
  let startW = 0;

  const onMove = (ev: PointerEvent) => {
    if (!activeCol) return;
    const delta = ev.clientX - startX;
    colWidths[activeCol] = clamp(startW + delta, MIN[activeCol], MAX[activeCol]);
  };

  const cleanup = () => {
    activeCol = null;
    document.removeEventListener('pointermove', onMove);
    document.removeEventListener('pointerup', onUp);
    document.removeEventListener('visibilitychange', cleanup);
    window.removeEventListener('blur', cleanup);
    document.body.style.cursor = '';
  };

  const onUp = () => cleanup();

  const onResizeStart = (col: ColKey, ev: PointerEvent) => {
    ev.preventDefault();
    activeCol = col;
    startX = ev.clientX;
    startW = colWidths[col];
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp, { once: true });
    document.addEventListener('visibilitychange', cleanup);
    window.addEventListener('blur', cleanup);
    document.body.style.cursor = 'col-resize';
  };

  onUnmounted(() => cleanup());

  return { colWidths, onResizeStart };
}
