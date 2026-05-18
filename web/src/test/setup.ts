// web/src/test/setup.ts
// Global setup for Vitest. Imports the full theme.css so all component tests
// have CSS custom properties available via getComputedStyle.

import '../styles/theme.css';
import { beforeEach } from 'vitest';

// Reset HTML data attributes between tests so theme/accent/motion don't leak.
beforeEach(() => {
  const html = document.documentElement;
  html.dataset.theme = 'dark';
  html.dataset.accent = 'lime';
  html.dataset.motion = 'spring';
});
