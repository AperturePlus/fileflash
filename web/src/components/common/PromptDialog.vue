<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ui, uiState } from '../../utils/ui';

const active = computed(() => uiState.prompt);
const value = ref('');

watch(
  active,
  (current) => {
    value.value = current?.defaultValue || '';
  },
  { immediate: true },
);

const handleClose = () => {
  ui.resolvePrompt(null);
};

const handleConfirm = () => {
  ui.resolvePrompt(value.value);
};
</script>

<template>
  <transition name="modal-fade">
    <div v-if="active" class="modal-overlay" @click.self="handleClose">
      <div class="modal-dialog">
        <header class="modal-header">
          <h3 class="modal-title">{{ active.title }}</h3>
          <button class="modal-close" @click="handleClose">&times;</button>
        </header>
        <div class="modal-body">
          <p class="message">{{ active.message }}</p>
          <input
            v-model="value"
            class="input"
            :placeholder="active.placeholder"
            :readonly="Boolean(active.readonly)"
            @keydown.enter.prevent="handleConfirm"
            @keydown.esc.prevent="handleClose"
          />
        </div>
        <footer class="modal-footer">
          <button class="btn btn-secondary" @click="handleClose">{{ active.cancelText }}</button>
          <button class="btn" :class="active.danger ? 'btn-danger' : 'btn-primary'" @click="handleConfirm">
            {{ active.confirmText }}
          </button>
        </footer>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(15, 23, 42, 0.56);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 3550;
}

.modal-dialog {
  width: min(92vw, 500px);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
}

.modal-header,
.modal-footer {
  padding: 14px 16px;
  display: flex;
  align-items: center;
}

.modal-header {
  justify-content: space-between;
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  margin: 0;
  font-size: 1rem;
}

.modal-close {
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 20px;
  cursor: pointer;
}

.modal-body {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.45;
}

.input {
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-primary);
  padding: 0 10px;
  color: var(--color-text-primary);
}

.modal-footer {
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid var(--color-border);
}

.btn {
  height: 34px;
  border-radius: 8px;
  padding: 0 12px;
  border: 1px solid transparent;
  cursor: pointer;
}

.btn-secondary {
  background: var(--color-bg-primary);
  border-color: var(--color-border);
}

.btn-primary {
  background: var(--color-primary);
  color: var(--color-text-on-primary);
}

.btn-danger {
  background: var(--color-danger-light);
  border-color: #fca5a5;
  color: var(--color-danger-dark);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-fade-enter-active .modal-dialog,
.modal-fade-leave-active .modal-dialog {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-dialog,
.modal-fade-leave-to .modal-dialog {
  transform: scale(0.95) translateY(10px);
}
</style>
