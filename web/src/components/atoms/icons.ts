// web/src/components/atoms/icons.ts
// SVG path-data registry. Each entry is the `d` attribute of a single <path>.
// Icons are designed on a 24x24 grid with stroke-width 2, line-cap round,
// line-join round. Source: hand-curated minimalist set, matches B aesthetic.

export const ICONS = {
  chevronDown: 'M6 9l6 6 6-6',
  chevronRight: 'M9 6l6 6-6 6',
  chevronLeft: 'M15 6l-6 6 6 6',
  chevronUp: 'M6 15l6-6 6 6',
  search: 'M11 4a7 7 0 1 0 4.9 12l4.6 4.6 1.4-1.4-4.6-4.6A7 7 0 0 0 11 4',
  menu: 'M3 6h18M3 12h18M3 18h18',
  close: 'M6 6l12 12M18 6L6 18',
  check: 'M4 12l5 5L20 6',
  upload: 'M12 4v12M6 10l6-6 6 6M4 20h16',
  download: 'M12 20V8M6 14l6 6 6-6M4 4h16',
  more: 'M5 12h.01M12 12h.01M19 12h.01',
  eye: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  eyeOff: 'M3 3l18 18M10.5 10.5a3 3 0 0 0 4 4M9 5.5C9.9 5.2 10.9 5 12 5c6.5 0 10 7 10 7-.5 1-1.4 2.3-2.7 3.4M5.3 8.4C3.5 9.9 2 12 2 12s3.5 7 10 7c1.6 0 3-.4 4.3-1',
  plus: 'M12 5v14M5 12h14',
  trash: 'M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6',
  folder: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6',
  share: 'M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13',
  sun: 'M12 5V2m0 20v-3m7-7h3M2 12h3m11.3 4.3l2.1 2.1M5.6 5.6l2.1 2.1m8.6 0l2.1-2.1m-12.8 12.8l2.1-2.1M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8',
  moon: 'M21 13a8 8 0 1 1-10-10a7 7 0 0 0 10 10',
  star: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z',
  arrowUp: 'M12 19V5M5 12l7-7 7 7',
  arrowDown: 'M12 5v14M5 12l7 7 7-7',
  folderPlus: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7zM12 11v6M9 14h6',
} as const;

export type IconName = keyof typeof ICONS;
