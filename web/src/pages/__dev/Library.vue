<script setup lang="ts">
import { ref } from 'vue';
import * as A from '../../components/atoms';
import * as M from '../../components/molecules';
import * as F from '../../components/organisms/files';
import * as Sh from '../../components/organisms/sharing';
import * as Tr from '../../components/organisms/trash';
import * as Sa from '../../components/organisms/share';
import { useFilePreview } from '../../composables/useFilePreview';
import type { FileItem } from '../../types/file';

const sections = [
  'Tokens', 'Atoms · Text', 'Atoms · Numbers', 'Atoms · Visual', 'Atoms · Form',
  'Molecules · Action', 'Molecules · Input', 'Molecules · Display', 'Molecules · Nav',
  'Organisms · Files', 'Organisms · Sharing', 'Organisms · Trash', 'Organisms · Share',
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

// Files organism demo state
const filesViewMode = ref<'list' | 'grid'>('list');
const filesSortKey = ref<'name' | 'size' | 'updatedAt'>('name');
const filesSortDirection = ref<'asc' | 'desc'>('asc');
const filesSearch = ref('');
const filesSelection = ref(new Set<string>(['demo-a']));
const filesRenamingId = ref<string | null>(null);
const filesRenameValue = ref('');

// Sharing / Trash / Share demo state
const sharedSelection = ref(new Set<string>());
const sharedDemoItems = [
  { itemType: 'file' as const, id: 's1', name: 'plan.docx', size: 4096, sharedBy: 'alice', permission: 'read' as const, sharedAt: '2026-05-09T10:00:00Z' },
  { itemType: 'folder' as const, id: 's2', name: 'designs', size: 0, sharedBy: 'bob', permission: 'write' as const, sharedAt: '2026-05-08T12:30:00Z' },
];
const linksDemoItems = [
  { shareId: 'l1', shareLink: 'abc123', itemType: 'file' as const, itemInfo: { id: 'f1', name: 'report.pdf', size: 1024, mimeType: 'application/pdf' }, settings: { passwordProtected: false, expireAt: null, allowDownload: true, allowPreview: true }, createdAt: '2026-05-01T00:00:00Z', visitCount: 12, downloadCount: 4 },
];
const trashDemoItems = [
  { itemType: 'file' as const, id: 't1', name: 'draft.md', originalPath: '/notes', size: 200, deletedAt: '2026-05-09T18:00:00Z', autoDeleteAt: '2026-06-08T18:00:00Z', daysUntilPermanentDelete: 27, canRestore: true, restoreConflicts: false },
  { itemType: 'file' as const, id: 't2', name: 'expired.zip', originalPath: '/archives', size: 1024, deletedAt: '2026-05-05T08:00:00Z', autoDeleteAt: '2026-05-15T08:00:00Z', daysUntilPermanentDelete: 3, canRestore: false, restoreConflicts: true },
];
const shareDemo = { shareId: 's', shareLink: 'xyz789', itemType: 'file' as const, itemInfo: { id: 'f', name: 'big-report.pdf', size: 1_245_184, mimeType: 'application/pdf' }, settings: { passwordProtected: true, expireAt: '2026-12-01', allowDownload: true, allowPreview: true }, createdAt: '2026-05-01T00:00:00Z' };
const sharePassword = ref('');

const demoItems = [
  {
    id: 'demo-a', name: 'README.md', itemType: 'file' as const,
    size: 4321, mimeType: 'text/markdown', ownerName: 'demo',
    createdAt: '2026-05-01T00:00:00Z', updatedAt: '2026-05-09T10:11:00Z',
    folderId: 'root', isStarred: true,
  },
  {
    id: 'demo-b', name: 'projects', itemType: 'folder' as const,
    size: 0, ownerName: 'demo',
    createdAt: '2026-05-01T00:00:00Z', updatedAt: '2026-05-08T08:00:00Z',
    parentFolderId: null, isStarred: false,
  },
  {
    id: 'demo-c', name: 'video.mp4', itemType: 'file' as const,
    size: 12_500_000, mimeType: 'video/mp4', ownerName: 'demo',
    createdAt: '2026-04-22T00:00:00Z', updatedAt: '2026-04-22T18:30:00Z',
    folderId: 'root', isStarred: false,
  },
];

const demoUpload = [
  { id: 'u1', name: 'archive.zip', progress: { percentage: 64 } },
  { id: 'u2', name: 'snapshot.png', progress: { percentage: 100 } },
];

const { previewFile: filesPreviewFile, openPreview: openFilesPreview, closePreview: closeFilesPreview } = useFilePreview();
const filesLastInteraction = ref('');

function demoOnSelect(payload: { item: { id: string }; modifiers: { shift: boolean } }) {
  filesLastInteraction.value = `select ${payload.item.id}${payload.modifiers.shift ? ' (shift)' : ''}`;
  const next = new Set(filesSelection.value);
  if (next.has(payload.item.id)) next.delete(payload.item.id);
  else next.add(payload.item.id);
  filesSelection.value = next;
}

function demoOnActivate(item: { id: string; itemType: 'file' | 'folder'; name: string }) {
  if (item.itemType === 'file') {
    filesLastInteraction.value = `activate file ${item.name}`;
    openFilesPreview({
      itemType: 'file',
      id: item.id,
      name: item.name,
      size: 0,
      mimeType: 'text/plain',
      ownerName: 'demo',
      createdAt: '',
      updatedAt: '',
      folderId: 'root',
    } as FileItem);
  } else {
    filesLastInteraction.value = `activate folder ${item.name}`;
  }
}

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
      <section v-if="activeSection === 'Organisms · Files'">
        <A.Text as="h1" variant="h1">Organisms · Files</A.Text>

        <A.Text variant="label">EmptyState · variants</A.Text>
        <div class="grid">
          <F.EmptyState variant="loading" />
          <F.EmptyState variant="empty" />
          <F.EmptyState variant="no-results" query="missing.pdf" />
        </div>

        <A.Text variant="label">UploadProgressTray</A.Text>
        <F.UploadProgressTray :tasks="demoUpload" />

        <A.Text variant="label">BulkActionBar</A.Text>
        <F.BulkActionBar :count="filesSelection.size" @clear="filesSelection = new Set()" />

        <A.Text variant="label">FileToolbar</A.Text>
        <F.FileToolbar
          :view-mode="filesViewMode"
          :sort-key="filesSortKey"
          :sort-direction="filesSortDirection"
          :search-query="filesSearch"
          :is-searching="filesSearch.length > 0"
          @update:view-mode="filesViewMode = $event"
          @update:search-query="filesSearch = $event"
          @clear-search="filesSearch = ''"
          @sort="(k) => filesSortKey = k"
          @create-folder="() => {}"
          @upload="() => {}"
        />

        <A.Text variant="label">FileTable · {{ filesViewMode }}</A.Text>
        <F.FileTable
          :mode="filesViewMode"
          :items="demoItems"
          :selection="filesSelection"
          :renaming-id="filesRenamingId"
          :rename-value="filesRenameValue"
          :sort-key="filesSortKey"
          :sort-direction="filesSortDirection"
          @update:rename-value="filesRenameValue = $event"
          @toggle-select="(id) => { const next = new Set(filesSelection); if (next.has(id)) next.delete(id); else next.add(id); filesSelection = next; }"
          @select="demoOnSelect"
          @activate="demoOnActivate"
          @clear-selection="filesSelection = new Set()"
          @start-rename="(item) => { filesRenamingId = item.id; filesRenameValue = item.name; }"
          @cancel-rename="filesRenamingId = null"
          @finish-rename="filesRenamingId = null"
          @sort="(k) => filesSortKey = k"
        />
        <A.Text variant="data">Last interaction: {{ filesLastInteraction || '—' }}</A.Text>
        <F.FilePreviewDialog :file="filesPreviewFile" @close="closeFilesPreview" />
      </section>

      <section v-if="activeSection === 'Organisms · Sharing'">
        <A.Text as="h1" variant="h1">Organisms · Sharing</A.Text>

        <A.Text variant="label">SharedReceivedTable</A.Text>
        <Sh.SharedReceivedTable :items="sharedDemoItems" :selection="sharedSelection"
          @toggle="(id) => { const next = new Set(sharedSelection); next.has(id) ? next.delete(id) : next.add(id); sharedSelection = next; }"
          @toggle-all="(n) => sharedSelection = n ? new Set(sharedDemoItems.map((i) => i.id)) : new Set()"
          @accept="() => {}" />

        <A.Text variant="label">SharedReceivedTable · empty</A.Text>
        <F.EmptyState variant="empty" message="No files shared with you." />

        <A.Text variant="label">SharedLinksTable</A.Text>
        <Sh.SharedLinksTable :items="linksDemoItems" @copy="() => {}" @delete="() => {}" />

        <A.Text variant="label">SharedBatchBar · count = 2</A.Text>
        <Sh.SharedBatchBar :count="2" @accept="() => {}" @clear="() => {}" />
      </section>

      <section v-if="activeSection === 'Organisms · Trash'">
        <A.Text as="h1" variant="h1">Organisms · Trash</A.Text>

        <A.Text variant="label">TrashTable</A.Text>
        <Tr.TrashTable :items="trashDemoItems" @restore="() => {}" @permanent-delete="() => {}" />

        <A.Text variant="label">TrashTable · empty</A.Text>
        <F.EmptyState variant="empty" message="Recycle bin is empty." />
      </section>

      <section v-if="activeSection === 'Organisms · Share'">
        <A.Text as="h1" variant="h1">Organisms · Share</A.Text>

        <A.Text variant="label">ShareInfoCard</A.Text>
        <Sa.ShareInfoCard :share="shareDemo" />

        <A.Text variant="label">ShareAccessPanel · password mode</A.Text>
        <Sa.ShareAccessPanel
          :password-protected="true" :password="sharePassword" :is-accessing="false"
          status-message="Awaiting password."
          @update:password="sharePassword = $event" @request-access="() => {}" />

        <A.Text variant="label">ShareAccessPanel · open mode</A.Text>
        <Sa.ShareAccessPanel
          :password-protected="false" password="" :is-accessing="false"
          @update:password="() => {}" @request-access="() => {}" />

        <A.Text variant="label">ShareActionsPanel · file</A.Text>
        <Sa.ShareActionsPanel
          :is-file="true" :is-folder="false" :can-preview="true" :can-download="true"
          :is-previewing="false" :is-downloading="false" :is-saving="false"
          @preview="() => {}" @download="() => {}" @save="() => {}" />

        <A.Text variant="label">ShareActionsPanel · folder</A.Text>
        <Sa.ShareActionsPanel
          :is-file="false" :is-folder="true" :can-preview="false" :can-download="false"
          :is-previewing="false" :is-downloading="false" :is-saving="false"
          @preview="() => {}" @download="() => {}" @save="() => {}" />
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
