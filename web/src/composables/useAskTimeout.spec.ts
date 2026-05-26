import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ref } from 'vue';
import { useAskTimeout } from './useAskTimeout';

describe('useAskTimeout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('counts down from askedAt + timeoutSec', () => {
    const askedAt = ref('2026-05-26T12:00:00.000Z');
    const timeoutSec = ref(120);
    vi.setSystemTime(new Date('2026-05-26T12:00:30.000Z'));
    const { remainingSec, formatted, expired } = useAskTimeout(askedAt, timeoutSec);
    expect(remainingSec.value).toBe(90);
    expect(formatted.value).toBe('01:30');
    expect(expired.value).toBe(false);

    vi.setSystemTime(new Date('2026-05-26T12:02:01.000Z'));
    vi.advanceTimersByTime(1000);
    expect(expired.value).toBe(true);
    expect(remainingSec.value).toBe(0);
    expect(formatted.value).toBe('00:00');
  });

  it('returns expired immediately when askedAt is missing', () => {
    const askedAt = ref<string | undefined>(undefined);
    const timeoutSec = ref(60);
    const { expired, formatted } = useAskTimeout(askedAt, timeoutSec);
    expect(expired.value).toBe(true);
    expect(formatted.value).toBe('00:00');
  });
});
