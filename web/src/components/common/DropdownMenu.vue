<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';

const isVisible = ref(false);
const menu = ref<HTMLDivElement | null>(null);
const trigger = ref<HTMLDivElement | null>(null);

// Style for the menu, to be calculated dynamically
const menuStyle = ref({});

const calculatePosition = () => {
  if (!trigger.value) return;

  const triggerRect = trigger.value.getBoundingClientRect();
  const spaceRight = window.innerWidth - triggerRect.right;
  const menuWidth = 200; // Estimated or actual width of the menu

  if (spaceRight < menuWidth) {
    // Not enough space on the right, align to the right edge of the trigger
    menuStyle.value = { right: '0' };
  } else {
    // Enough space on the right, align to the left edge
    menuStyle.value = { left: '0' };
  }
};

const toggle = async () => {
  const currentlyVisible = isVisible.value;
  if (!currentlyVisible) {
    // If we are about to show the menu, make it visible first, then calculate position
    isVisible.value = true;
    await nextTick(); // Wait for the DOM to update
    calculatePosition();
  } else {
    // If we are hiding it, just hide
    isVisible.value = false;
  }
};

const handleClickOutside = (event: MouseEvent) => {
  if (
    isVisible.value &&
    menu.value &&
    !menu.value.contains(event.target as Node) &&
    trigger.value &&
    !trigger.value.contains(event.target as Node)
  ) {
    isVisible.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<template>
  <div class="dropdown" @click.stop>
    <div ref="trigger" @click="toggle" class="dropdown-trigger">
      <slot name="trigger"></slot>
    </div>
    <transition name="fade">
      <div v-if="isVisible" ref="menu" class="dropdown-menu" :style="menuStyle">
        <slot name="content"></slot>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.dropdown {
  position: relative;
  display: inline-block;
}

.dropdown-trigger {
  cursor: pointer;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + var(--spacing-sm));
  /* right: 0; is now handled dynamically */
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  box-shadow: var(--shadow-md);
  min-width: 200px;
  z-index: 1000;
  overflow: hidden;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.96);
}
</style> 