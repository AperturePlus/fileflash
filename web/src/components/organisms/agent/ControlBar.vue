<script setup lang="ts">
import Button from '../../molecules/Button.vue';
import { useLocaleStore } from '../../../store/locale';
import type { MsgStatus } from '../../../composables/useAgentSession';

defineProps<{
  status: MsgStatus;
  hasPlanRiskStep?: boolean;
}>();

defineEmits<{
  pause: [];
  resume: [];
  skip: [];
  approve: [];
  deny: [];
  cancel: [];
}>();

const localeStore = useLocaleStore();
const t = localeStore.t;
</script>

<template>
  <div class="ff-ctrl">
    <Button
      v-if="status === 'running'"
      variant="ghost"
      size="sm"
      @click.stop="$emit('pause')"
    >
      {{ t('agent.v2.turn.controls.pause') }}
    </Button>

    <Button
      v-if="status === 'paused'"
      variant="primary"
      size="sm"
      @click.stop="$emit('resume')"
    >
      {{ t('agent.v2.turn.controls.resume') }}
    </Button>

    <Button
      v-if="status === 'running' || status === 'paused'"
      variant="ghost"
      size="sm"
      @click.stop="$emit('skip')"
    >
      {{ t('agent.v2.turn.controls.skip') }}
    </Button>

    <template v-if="hasPlanRiskStep && status === 'running'">
      <Button variant="primary" size="sm" @click.stop="$emit('approve')">
        {{ t('agent.v2.turn.controls.approve') }}
      </Button>
      <Button variant="ghost" size="sm" @click.stop="$emit('deny')">
        {{ t('agent.v2.turn.controls.deny') }}
      </Button>
    </template>

    <Button
      v-if="
        status === 'pending' ||
        status === 'running' ||
        status === 'paused' ||
        status === 'waiting_for_user'
      "
      variant="ghost"
      size="sm"
      @click.stop="$emit('cancel')"
    >
      {{ t('agent.v2.turn.cancel') }}
    </Button>
  </div>
</template>

<style scoped>
.ff-ctrl {
  display: flex;
  gap: var(--sp-sm);
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>
