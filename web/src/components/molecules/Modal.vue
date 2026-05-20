<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue';

const props = withDefaults(
  defineProps<{
    open: boolean;
    size?: 'sm' | 'md' | 'lg';
    closeOnBackdrop?: boolean;
  }>(),
  { size: 'md', closeOnBackdrop: true },
);

const emit = defineEmits<{ close: [] }>();

const onKey = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.open) emit('close');
};

const onBackdrop = () => {
  if (props.closeOnBackdrop) emit('close');
};

onMounted(() => document.addEventListener('keydown', onKey));
onBeforeUnmount(() => document.removeEventListener('keydown', onKey));
</script>

<template>
  <Teleport to="body">
    <Transition name="ff-modal-fade">
      <div v-if="open" class="ff-modal" role="dialog" aria-modal="true">
        <div class="ff-modal__scrim" @click="onBackdrop" />
        <div class="ff-modal__panel" :class="`ff-modal__panel--${size}`">
          <header v-if="$slots.header" class="ff-modal__head">
            <slot name="header" />
          </header>
          <div class="ff-modal__body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="ff-modal__foot">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ff-modal {
  position: fixed; inset: 0;
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.ff-modal__scrim {
  position: absolute; inset: 0;
  background: rgb(0 0 0 / 0.55);
}
.ff-modal__panel {
  position: relative;
  display: flex; flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: 0;
  padding: var(--sp-xl);
  max-height: 90vh;
  width: 100%;
}
.ff-modal__panel--sm { max-width: 360px; }
.ff-modal__panel--md { max-width: 560px; }
.ff-modal__panel--lg { max-width: 920px; }

.ff-modal__head {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: var(--sp-md);
  padding-bottom: var(--sp-sm);
  border-bottom: 1px solid var(--border-default);
}
.ff-modal__body { flex: 1 1 auto; overflow: auto; }
.ff-modal__foot {
  margin-top: var(--sp-md);
  padding-top: var(--sp-sm);
  border-top: 1px solid var(--border-default);
  display: flex; justify-content: flex-end; gap: var(--sp-sm);
}

.ff-modal-fade-enter-active,
.ff-modal-fade-leave-active { transition: opacity 200ms var(--mo-easing); }
.ff-modal-fade-enter-from,
.ff-modal-fade-leave-to { opacity: 0; }
</style>
