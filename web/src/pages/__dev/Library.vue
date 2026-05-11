<script setup lang="ts">
import { ref } from 'vue';
import * as A from '../../components/atoms';
import * as M from '../../components/molecules';

const sections = [
  'Tokens', 'Atoms · Text', 'Atoms · Numbers', 'Atoms · Visual', 'Atoms · Form',
  'Molecules · Action', 'Molecules · Input', 'Molecules · Display', 'Molecules · Nav',
] as const;
type Section = typeof sections[number];

const activeSection = ref<Section>('Tokens');

// Theme controls — live-edit <html> dataset.
const theme = ref<'dark' | 'light'>(
  (document.documentElement.dataset.theme as 'dark' | 'light') ?? 'dark',
);
const accent = ref<'lime' | 'amber' | 'oxide'>(
  (document.documentElement.dataset.accent as 'lime' | 'amber' | 'oxide') ?? 'lime',
);
const motion = ref<'spring' | 'tight' | 'reduced'>(
  (document.documentElement.dataset.motion as 'spring' | 'tight' | 'reduced') ?? 'spring',
);

function setTheme(v: string | number)  { theme.value  = v as typeof theme.value;  document.documentElement.dataset.theme  = String(v); }
function setAccent(v: string | number) { accent.value = v as typeof accent.value; document.documentElement.dataset.accent = String(v); }
function setMotion(v: string | number) { motion.value = v as typeof motion.value; document.documentElement.dataset.motion = String(v); }

// Demo state
const text = ref('');
const checked = ref(false);
const radio = ref('a');
const toggled = ref(false);
const tab = ref(0);

const themeOpts = [
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
];
const accentOpts = [
  { value: 'lime', label: 'Lime' },
  { value: 'amber', label: 'Amber' },
  { value: 'oxide', label: 'Oxide' },
];
const motionOpts = [
  { value: 'spring', label: 'Spring' },
  { value: 'tight', label: 'Tight' },
  { value: 'reduced', label: 'Reduced' },
];

const swatches = [
  '--surface-base',
  '--surface-raised',
  '--surface-inset',
  '--border-default',
  '--border-subtle',
  '--text-primary',
  '--text-secondary',
  '--text-dim',
  '--ac',
  '--status-success',
  '--status-warning',
  '--status-error',
  '--status-info',
];
</script>

<template>
  <div class="lib">
    <aside class="lib-side">
      <A.Text variant="display">FF Library</A.Text>
      <A.Text variant="small">Atoms + Molecules · dev only</A.Text>

      <div class="lib-controls">
        <A.Text variant="label">Theme</A.Text>
        <M.SegmentedControl :model-value="theme" :options="themeOpts" @update:model-value="setTheme" />
        <A.Text variant="label">Accent</A.Text>
        <M.SegmentedControl :model-value="accent" :options="accentOpts" @update:model-value="setAccent" />
        <A.Text variant="label">Motion</A.Text>
        <M.SegmentedControl :model-value="motion" :options="motionOpts" @update:model-value="setMotion" />
      </div>

      <nav class="lib-nav">
        <M.MenuItem v-for="s in sections" :key="s" @click="activeSection = s">{{ s }}</M.MenuItem>
      </nav>
    </aside>

    <main class="lib-main">
      <section v-if="activeSection === 'Tokens'">
        <A.Text as="h1" variant="h1">Design Tokens</A.Text>
        <p>See <code>web/src/styles/tokens/*.css</code> for the full table. The controls in the sidebar live-switch them.</p>
        <div class="swatches">
          <div class="sw" v-for="t in swatches" :key="t">
            <span class="sw-block" :style="{ background: `var(${t})` }" />
            <A.Text variant="data">{{ t }}</A.Text>
          </div>
        </div>
      </section>

      <section v-if="activeSection === 'Atoms · Text'">
        <A.Text as="h1" variant="h1">Atoms · Text</A.Text>
        <div class="grid">
          <div><A.Text variant="display">Display 32</A.Text></div>
          <div><A.Text as="h1" variant="h1">H1 22</A.Text></div>
          <div><A.Text as="h2" variant="h2">H2 17</A.Text></div>
          <div><A.Text variant="body">Body 13.5 — 中英混排测试 / Mixed CJK + Latin</A.Text></div>
          <div><A.Text variant="small">Small 12</A.Text></div>
          <div><A.Text variant="label">LABEL · 10</A.Text></div>
          <div><A.Text variant="data">DATA · 0.05 MB · 12:00</A.Text></div>
        </div>
      </section>

      <section v-if="activeSection === 'Atoms · Numbers'">
        <A.Text as="h1" variant="h1">Atoms · Numbers</A.Text>
        <div class="grid">
          <A.MonoNumber value="2.4 MB" />
          <A.MonoNumber value="100%" accent />
          <A.KeyHint :keys="['Ctrl', 'K']" />
          <A.KeyHint :keys="['Esc']" />
        </div>
      </section>

      <section v-if="activeSection === 'Atoms · Visual'">
        <A.Text as="h1" variant="h1">Atoms · Visual</A.Text>
        <div class="grid">
          <A.Bar :value="0.64" />
          <A.Bar :value="0.4" tone="warning" />
          <A.Bar :value="0.9" tone="error" />
          <div class="dots"><A.Dot /><A.Dot tone="success" /><A.Dot tone="warning" /><A.Dot tone="error" /><A.Dot tone="info" /></div>
          <A.Divider />
          <A.Spinner label="Loading library" />
          <A.Surface elevation="raised" bordered style="padding:12px;">Surface raised+bordered</A.Surface>
        </div>
        <div class="grid">
          <A.Icon name="search" /><A.Icon name="upload" /><A.Icon name="folder" /><A.Icon name="trash" /><A.Icon name="moon" /><A.Icon name="sun" />
        </div>
      </section>

      <section v-if="activeSection === 'Atoms · Form'">
        <A.Text as="h1" variant="h1">Atoms · Form</A.Text>
        <div class="grid">
          <A.Input v-model="text" placeholder="Type…" />
          <A.Input v-model="text" placeholder="Disabled" disabled />
          <A.Input v-model="text" placeholder="Invalid" invalid />
          <A.Checkbox v-model="checked" label="Accept terms" />
          <A.Radio v-model="radio" value="a" name="demo-r" label="Option A" />
          <A.Radio v-model="radio" value="b" name="demo-r" label="Option B" />
          <A.Toggle v-model="toggled" label="Enabled" />
        </div>
      </section>

      <section v-if="activeSection === 'Molecules · Action'">
        <A.Text as="h1" variant="h1">Molecules · Action</A.Text>
        <div class="grid">
          <M.Button>Primary</M.Button>
          <M.Button variant="ghost">Ghost</M.Button>
          <M.Button variant="danger">Danger</M.Button>
          <M.Button icon="upload">Upload</M.Button>
          <M.Button loading>Loading</M.Button>
          <M.Button disabled>Disabled</M.Button>
          <M.Button size="sm">Small</M.Button>
          <M.IconButton icon="close" label="Close" />
          <M.IconButton icon="upload" label="Upload" variant="primary" />
        </div>
      </section>

      <section v-if="activeSection === 'Molecules · Input'">
        <A.Text as="h1" variant="h1">Molecules · Input</A.Text>
        <div class="grid">
          <M.TextField v-model="text" label="Username" hint="Min 3 characters" />
          <M.TextField v-model="text" label="Password" type="password" error="Required" />
          <M.SearchField v-model="text" placeholder="Search files…" />
        </div>
      </section>

      <section v-if="activeSection === 'Molecules · Display'">
        <A.Text as="h1" variant="h1">Molecules · Display</A.Text>
        <div class="grid">
          <M.Badge>Live</M.Badge>
          <M.Badge tone="warning">Pending</M.Badge>
          <M.Badge tone="error">Failed</M.Badge>
          <M.Badge tone="info">Info</M.Badge>
          <M.Badge tone="accent">Accent</M.Badge>
          <M.Tag>design</M.Tag>
          <M.Tag removable>removable</M.Tag>
          <M.StatBlock label="TOTAL FILES" value="2,486" />
          <M.StatBlock label="STORAGE" value="124.7 GB" :delta="3" />
          <M.StatBlock label="ERRORS" value="12" :delta="-2" />
          <M.ProgressBar :value="0.64" />
          <M.ProgressBar :value="0.92" tone="warning" />
        </div>
      </section>

      <section v-if="activeSection === 'Molecules · Nav'">
        <A.Text as="h1" variant="h1">Molecules · Nav</A.Text>
        <div class="grid">
          <div class="row">
            <M.BreadcrumbItem href="/">Home</M.BreadcrumbItem>
            <M.BreadcrumbItem href="/files">Files</M.BreadcrumbItem>
            <M.BreadcrumbItem>Current</M.BreadcrumbItem>
          </div>
          <div class="row">
            <M.Tab :active="tab === 0" @click="tab = 0">Tab one</M.Tab>
            <M.Tab :active="tab === 1" @click="tab = 1">Tab two</M.Tab>
            <M.Tab :active="tab === 2" @click="tab = 2">Tab three</M.Tab>
          </div>
          <M.MenuItem icon="upload" :key-hint="['Ctrl','U']">Upload file</M.MenuItem>
          <M.MenuItem icon="trash" variant="danger">Delete</M.MenuItem>
          <M.Toolbar>
            <M.IconButton icon="upload" label="Upload" />
            <M.IconButton icon="download" label="Download" />
            <template #split>
              <M.IconButton icon="trash" label="Delete" />
            </template>
          </M.Toolbar>
          <div class="row">
            <M.Avatar name="Alice Wong" />
            <M.Avatar name="B" size="sm" />
            <M.Avatar name="" />
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.lib { display: grid; grid-template-columns: 260px 1fr; height: 100vh; background: var(--surface-base); color: var(--text-primary); font-family: var(--font-sans); }
.lib-side { padding: 18px; border-right: 1px solid var(--border-default); display: flex; flex-direction: column; gap: 14px; overflow: auto; }
.lib-controls { display: flex; flex-direction: column; gap: 6px; }
.lib-nav { display: flex; flex-direction: column; gap: 0; margin-top: 12px; }
.lib-main { padding: 32px; overflow: auto; display: flex; flex-direction: column; gap: 28px; }
.grid { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; padding: 12px 0; }
.row { display: inline-flex; align-items: center; gap: 8px; }
.dots { display: inline-flex; gap: 6px; align-items: center; }
.swatches { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.sw { display: flex; align-items: center; gap: 10px; padding: 10px; border: 1px solid var(--border-subtle); }
.sw-block { width: 28px; height: 28px; border: 1px solid var(--border-subtle); flex-shrink: 0; }
code { font-family: var(--font-mono); font-size: var(--text-data); color: var(--ac); }
</style>
