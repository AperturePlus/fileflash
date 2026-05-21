<script setup lang="ts">
import { ref } from 'vue';

const props = withDefaults(
  defineProps<{
    accept?: string;
    multiple?: boolean;
    disabled?: boolean;
  }>(),
  { multiple: false },
);

const emit = defineEmits<{ files: [File[]] }>();

const inputEl = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);

const acceptMatchers = () =>
  (props.accept ?? '')
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);

const matchesAccept = (file: File) => {
  const list = acceptMatchers();
  if (!list.length) return true;
  const ext = '.' + (file.name.split('.').pop() ?? '').toLowerCase();
  const mime = file.type.toLowerCase();
  return list.some((m) => {
    if (m.startsWith('.')) return m === ext;
    if (m.endsWith('/*')) return mime.startsWith(m.slice(0, -1));
    return m === mime;
  });
};

const openPicker = () => {
  if (props.disabled) return;
  inputEl.value?.click();
};

const emitFiles = (raw: File[]) => {
  const filtered = raw.filter(matchesAccept);
  if (!filtered.length) return;
  const out = props.multiple ? filtered : [filtered[0]];
  emit('files', out);
};

const onChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  const files = target.files ? Array.from(target.files) : [];
  if (files.length) emitFiles(files);
  target.value = '';
};

const onDrop = (e: DragEvent) => {
  isDragging.value = false;
  if (props.disabled) return;
  const files = e.dataTransfer?.files ? Array.from(e.dataTransfer.files) : [];
  if (files.length) emitFiles(files);
};
</script>

<template>
  <div
    class="ff-drop"
    :class="{ 'is-dragging': isDragging, 'is-disabled': disabled }"
    role="button"
    tabindex="0"
    @click="openPicker"
    @keydown.enter.prevent="openPicker"
    @keydown.space.prevent="openPicker"
    @dragenter.prevent="isDragging = true"
    @dragover.prevent
    @dragleave.prevent="isDragging = false"
    @drop.prevent="onDrop"
  >
    <input
      ref="inputEl"
      type="file"
      class="ff-drop__input"
      :accept="accept"
      :multiple="multiple"
      :disabled="disabled"
      @change="onChange"
    />
    <span class="ff-drop__label">
      <slot>Drop file or click to browse</slot>
    </span>
  </div>
</template>

<style scoped>
.ff-drop {
  display: flex; align-items: center; justify-content: center;
  padding: var(--sp-lg);
  border: 1px dashed var(--border-default);
  background: var(--surface-inset);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 0;
  font-family: var(--font-mono);
  font-size: var(--text-label);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  transition: border-color var(--mo-duration-fast) var(--mo-easing),
              background var(--mo-duration-fast) var(--mo-easing);
  outline: none;
}
.ff-drop:hover, .ff-drop:focus-visible {
  border-color: var(--ac);
  color: var(--text-primary);
}
.ff-drop.is-dragging {
  border-color: var(--ac);
  background: color-mix(in srgb, var(--ac) 10%, var(--surface-inset));
  color: var(--text-primary);
}
.ff-drop.is-disabled { opacity: 0.5; cursor: not-allowed; }
.ff-drop__input { display: none; }
</style>
