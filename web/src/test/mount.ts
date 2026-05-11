// web/src/test/mount.ts
// Token-aware mount helper. Wraps @vue/test-utils so component tests can
// switch theme/accent/motion via options and assert against resolved CSS
// variable values.

import { mount as vtuMount, type MountingOptions } from '@vue/test-utils';
import type { Component } from 'vue';

export interface ThemeContext {
  theme?: 'dark' | 'light';
  accent?: 'lime' | 'amber' | 'oxide';
  motion?: 'spring' | 'tight' | 'reduced';
}

// The Vue Test Utils mount() generic types don't compose cleanly when we
// extract `context` from the options bag. Casting through `unknown` keeps
// callers' API unchanged while bypassing the structural mismatch.
export function mount<TComponent extends Component>(
  component: TComponent,
  options: MountingOptions<unknown> & { context?: ThemeContext } = {},
) {
  const { context, ...rest } = options;
  if (context) {
    const html = document.documentElement;
    if (context.theme) html.dataset.theme = context.theme;
    if (context.accent) html.dataset.accent = context.accent;
    if (context.motion) html.dataset.motion = context.motion;
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return vtuMount(component as any, rest as any);
}

/** Read a CSS variable from the document root after mount. */
export function readToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
