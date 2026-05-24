<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getSystemHealth, getRateLimitStatus } from '../../../api/system';
import { AdminTable, StatusBadge } from '../../../components/console';
import type { RateLimitRule, RateLimitStatus, SystemHealth } from '../../../types/system';

const health = ref<SystemHealth | null>(null);
const rateLimit = ref<RateLimitStatus | null>(null);

onMounted(async () => {
  const [h, r] = await Promise.all([getSystemHealth(), getRateLimitStatus()]);
  health.value = h;
  rateLimit.value = r;
});
</script>

<template>
  <section class="page">
    <header class="page__header"><h1>System</h1></header>

    <div v-if="health" class="health">
      <div class="health__item">
        <span>Virus Scan</span>
        <StatusBadge
          :value="health.virusScanEnabled ? 'on' : 'off'"
          :tone="health.virusScanEnabled ? 'positive' : 'neutral'"
        />
      </div>
      <div class="health__item">
        <span>Thumbnail</span>
        <StatusBadge
          :value="health.thumbnailGenerationEnabled ? 'on' : 'off'"
          :tone="health.thumbnailGenerationEnabled ? 'positive' : 'neutral'"
        />
      </div>
      <div class="health__item">
        <span>Registration Mail</span>
        <StatusBadge
          :value="health.registrationMailEnabled ? 'on' : 'off'"
          :tone="health.registrationMailEnabled ? 'positive' : 'neutral'"
        />
      </div>
      <div class="health__item">
        <span>Hash Computation</span>
        <StatusBadge
          :value="health.hashComputationEnabled ? 'on' : 'off'"
          :tone="health.hashComputationEnabled ? 'positive' : 'neutral'"
        />
      </div>
      <div class="health__item">
        <span>Active Upload Sessions</span>
        <strong class="num">{{ health.activeUploadSessions }}</strong>
      </div>
      <div class="health__item">
        <span>Max Concurrent</span>
        <strong class="num">{{ health.maxConcurrentUploads }}</strong>
      </div>
      <div class="health__targets">
        <span>Targets</span>
        <code v-for="t in health.platformTargets" :key="t">{{ t }}</code>
      </div>
    </div>

    <h2 class="page__section">Rate Limit Rules</h2>
    <AdminTable :items="rateLimit?.rules ?? []">
      <template #row="{ row }">
        <div class="rate-row">
          <strong>{{ (row as RateLimitRule).scope }}</strong>
          <small>
            {{ (row as RateLimitRule).limit }} / {{ (row as RateLimitRule).windowSeconds }}s ·
            used {{ (row as RateLimitRule).currentUsage }} ·
            blocked {{ (row as RateLimitRule).blockedRequests }}
          </small>
        </div>
      </template>
    </AdminTable>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--sp-lg);
}
.page__header h1 {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-h1);
  color: var(--text-primary);
  font-weight: var(--weight-medium);
  letter-spacing: var(--tracking-snug);
}
.health {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--sp-sm);
}
.health__item,
.health__targets {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-md);
  align-items: center;
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  font-family: var(--font-mono);
  font-size: var(--text-body);
  color: var(--text-secondary);
}
.health__item .num {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.health__targets { flex-wrap: wrap; }
.health__targets code {
  color: var(--text-primary);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  padding: 2px 8px;
  font-size: var(--text-small);
}
.page__section {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wider);
  margin: var(--sp-sm) 0 0;
  font-weight: var(--weight-regular);
}
.rate-row {
  display: flex;
  flex-direction: column;
  padding: 10px 14px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  gap: var(--sp-xs);
}
.rate-row strong {
  font-family: var(--font-mono);
  font-size: var(--text-body);
  color: var(--text-primary);
}
.rate-row small {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-small);
  font-variant-numeric: tabular-nums;
}
</style>
