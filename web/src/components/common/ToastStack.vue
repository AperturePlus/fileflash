<script setup lang="ts">
import { ui, uiState } from '../../utils/ui';
</script>

<template>
  <div class="toast-stack" aria-live="polite" aria-atomic="true">
    <transition-group name="toast-fade" tag="div" class="toast-group">
      <div
        v-for="item in uiState.toasts"
        :key="item.id"
        class="toast-item"
        :class="`toast-${item.type}`"
        @click="ui.dismissToast(item.id)"
      >
        <span>{{ item.message }}</span>
        <button class="close-btn" @click.stop="ui.dismissToast(item.id)">&times;</button>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 3600;
  pointer-events: none;
}

.toast-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.toast-item {
  min-width: 260px;
  max-width: 420px;
  pointer-events: auto;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  box-shadow: var(--shadow-md);
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.toast-success {
  border-color: #86efac;
  background: #f0fdf4;
  color: #166534;
}

.toast-error {
  border-color: #fca5a5;
  background: #fef2f2;
  color: #991b1b;
}

.toast-warning {
  border-color: #fcd34d;
  background: #fffbeb;
  color: #92400e;
}

.toast-info {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1e40af;
}

.close-btn {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.2s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>

