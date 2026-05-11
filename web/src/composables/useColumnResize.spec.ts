import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useColumnResize } from './useColumnResize';

function makePointerEvent(type: string, clientX: number): PointerEvent {
  return new PointerEvent(type, { clientX, bubbles: true });
}

describe('useColumnResize', () => {
  beforeEach(() => {
    document.body.style.cursor = '';
  });

  afterEach(() => {
    document.body.style.cursor = '';
  });

  it('starts from default px widths', () => {
    const c = useColumnResize();
    expect(c.colWidths.name).toBeGreaterThan(0);
    expect(c.colWidths.size).toBeGreaterThan(0);
    expect(c.colWidths.time).toBeGreaterThan(0);
  });

  it('drag updates the target column within clamp', () => {
    const c = useColumnResize();
    const startW = c.colWidths.name;
    c.onResizeStart('name', makePointerEvent('pointerdown', 100));
    document.dispatchEvent(makePointerEvent('pointermove', 200));
    expect(c.colWidths.name).toBe(Math.min(800, Math.max(120, startW + 100)));
    document.dispatchEvent(makePointerEvent('pointerup', 200));
  });

  it('clamps below MIN', () => {
    const c = useColumnResize();
    c.colWidths.size = 100;
    c.onResizeStart('size', makePointerEvent('pointerdown', 0));
    document.dispatchEvent(makePointerEvent('pointermove', -500));
    expect(c.colWidths.size).toBe(60);
    document.dispatchEvent(makePointerEvent('pointerup', -500));
  });

  it('clamps above MAX', () => {
    const c = useColumnResize();
    c.colWidths.size = 100;
    c.onResizeStart('size', makePointerEvent('pointerdown', 0));
    document.dispatchEvent(makePointerEvent('pointermove', 2000));
    expect(c.colWidths.size).toBe(200);
    document.dispatchEvent(makePointerEvent('pointerup', 2000));
  });

  it('cleanup on pointerup restores cursor', () => {
    const c = useColumnResize();
    c.onResizeStart('name', makePointerEvent('pointerdown', 0));
    expect(document.body.style.cursor).toBe('col-resize');
    document.dispatchEvent(makePointerEvent('pointerup', 0));
    expect(document.body.style.cursor).toBe('');
  });

  it('cleanup on visibilitychange stops dragging', () => {
    const c = useColumnResize();
    c.onResizeStart('name', makePointerEvent('pointerdown', 0));
    document.dispatchEvent(new Event('visibilitychange'));
    expect(document.body.style.cursor).toBe('');
    const w = c.colWidths.name;
    document.dispatchEvent(makePointerEvent('pointermove', 500));
    expect(c.colWidths.name).toBe(w);
  });
});
