<script setup lang="ts">
import { Text } from '../../atoms';
import { Button, TextField } from '../../molecules';

const props = defineProps<{
  passwordProtected: boolean;
  password: string;
  isAccessing: boolean;
  statusMessage?: string;
}>();

const emit = defineEmits<{
  (e: 'update:password', v: string): void;
  (e: 'request-access'): void;
}>();

void props;
</script>

<template>
  <div class="share-access">
    <Text variant="h2" as="h3" class="share-access__title">Access</Text>

    <div v-if="passwordProtected" class="share-access__form">
      <TextField
        :model-value="password"
        label="Password"
        type="password"
        placeholder="Enter password"
        @update:model-value="emit('update:password', $event)"
      />
      <Button :disabled="isAccessing" :loading="isAccessing" @click="emit('request-access')">
        {{ isAccessing ? 'Checking...' : 'Unlock' }}
      </Button>
    </div>

    <div v-else class="share-access__actions">
      <Button :disabled="isAccessing" :loading="isAccessing" @click="emit('request-access')">
        {{ isAccessing ? 'Accessing...' : 'Get Access' }}
      </Button>
    </div>

    <Text v-if="statusMessage" variant="small" class="share-access__hint">{{ statusMessage }}</Text>
  </div>
</template>

<style scoped>
.share-access {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  padding: 16px;
}
.share-access__title { margin: 0; }
.share-access__form {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: end;
}
.share-access__actions {
  display: flex;
  gap: 8px;
}
.share-access__hint {
  color: var(--text-dim);
}
</style>
