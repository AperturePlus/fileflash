<script setup lang="ts">
import { computed, ref } from 'vue';
import Button from '../../molecules/Button.vue';
import { useLocaleStore } from '../../../store/locale';
import { useAskTimeout } from '../../../composables/useAskTimeout';
import type { PendingAsk } from '../../../composables/useAgentSession';

const props = defineProps<{
  ask: PendingAsk;
  disabled?: boolean;
}>();

const emit = defineEmits<{ reply: [value: unknown] }>();

const localeStore = useLocaleStore();
const t = localeStore.t;

const askedAt = computed(() => props.ask.askedAt);
const timeoutSec = computed(() => props.ask.timeoutSec);
const { formatted, expired } = useAskTimeout(askedAt, timeoutSec);

const text = ref('');

const choices = computed<string[]>(() => {
  const choice = props.ask.schema?.choice;
  return Array.isArray(choice) ? choice.map((value) => String(value)) : [];
});

const timeoutLabel = computed(() =>
  t('agent.v2.turn.ask.timeout').replace('{value}', formatted.value),
);

const submit = () => {
  if (props.disabled || expired.value) return;
  const answer = text.value.trim();
  if (!answer) return;
  emit('reply', answer);
  text.value = '';
};

const onInput = (event: Event) => {
  text.value = (event.target as HTMLTextAreaElement).value;
};

const onKey = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    submit();
  }
};
</script>

<template>
  <section class="ff-askp" :class="{ 'is-expired': expired }">
    <header class="ff-askp__head">
      <span class="ff-askp__label">{{ t('agent.v2.turn.status.waiting_for_user') }}</span>
      <span class="ff-askp__timer">{{ timeoutLabel }}</span>
    </header>
    <p class="ff-askp__prompt">{{ ask.prompt }}</p>

    <div v-if="choices.length" class="ff-askp__choices">
      <Button
        v-for="choice in choices"
        :key="choice"
        variant="ghost"
        size="sm"
        :disabled="disabled || expired"
        @click="emit('reply', choice)"
      >
        {{ choice }}
      </Button>
    </div>

    <div v-else class="ff-askp__free">
      <textarea
        class="ff-askp__ta"
        :value="text"
        :disabled="disabled || expired"
        :placeholder="t('agent.v2.turn.ask.placeholder')"
        rows="2"
        @input="onInput"
        @keydown="onKey"
      />
      <Button
        variant="primary"
        size="sm"
        :disabled="!text.trim() || disabled || expired"
        @click="submit"
      >
        {{ t('agent.v2.turn.ask.send') }}
      </Button>
    </div>
  </section>
</template>

<style scoped>
.ff-askp {
  display: flex;
  flex-direction: column;
  gap: var(--sp-sm);
  padding: var(--sp-md);
  border: 1px solid var(--ac);
  background: var(--surface-base);
}
.ff-askp.is-expired {
  border-color: var(--text-tertiary);
  opacity: 0.6;
}
.ff-askp__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-md);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}
.ff-askp__label { color: var(--ac); }
.ff-askp__timer {
  color: var(--text-tertiary);
  white-space: nowrap;
}
.ff-askp__prompt {
  margin: 0;
  color: var(--text-primary);
  white-space: pre-wrap;
}
.ff-askp__choices {
  display: flex;
  gap: var(--sp-sm);
  flex-wrap: wrap;
}
.ff-askp__free {
  display: flex;
  gap: var(--sp-sm);
  align-items: flex-end;
}
.ff-askp__ta {
  flex: 1;
  resize: vertical;
  min-height: 48px;
  padding: var(--sp-sm) var(--sp-md);
  background: var(--surface-raised);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 0;
  font-family: var(--font-sans);
  font-size: var(--text-body);
  outline: none;
}
.ff-askp__ta:focus { border-color: var(--ac); }
.ff-askp__ta:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 720px) {
  .ff-askp__free {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
