import { computed, getCurrentScope, onScopeDispose, ref, watchEffect, type Ref } from 'vue';

export function useAskTimeout(
  askedAt: Ref<string | undefined | null>,
  timeoutSec: Ref<number>,
) {
  const now = ref<number>(Date.now());
  let timer: ReturnType<typeof setInterval> | null = null;

  const clearTimer = () => {
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  };

  const stopWatch = watchEffect(() => {
    clearTimer();
    now.value = Date.now();
    if (!askedAt.value || timeoutSec.value <= 0) return;
    const base = Date.parse(askedAt.value);
    if (Number.isNaN(base)) return;
    const deadlineMs = base + timeoutSec.value * 1000;
    timer = setInterval(() => {
      now.value = Date.now();
      if (now.value >= deadlineMs) {
        clearTimer();
      }
    }, 1000);
  });

  if (getCurrentScope()) {
    onScopeDispose(() => {
      clearTimer();
      stopWatch();
    });
  }

  const deadline = computed(() => {
    if (!askedAt.value) return null;
    const base = Date.parse(askedAt.value);
    if (Number.isNaN(base)) return null;
    return base + timeoutSec.value * 1000;
  });

  const remainingSec = computed(() => {
    if (deadline.value === null) return 0;
    return Math.max(0, Math.ceil((deadline.value - now.value) / 1000));
  });

  const expired = computed(() => deadline.value === null || remainingSec.value <= 0);

  const formatted = computed(() => {
    const total = remainingSec.value;
    const mm = String(Math.floor(total / 60)).padStart(2, '0');
    const ss = String(total % 60).padStart(2, '0');
    return `${mm}:${ss}`;
  });

  return { remainingSec, formatted, expired };
}
