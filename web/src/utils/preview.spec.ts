import { describe, expect, it } from 'vitest';
import { getPreviewCapabilities, normalizeMimeType, resolvePreviewMimeType } from './preview';

describe('utils/preview', () => {
  it('normalizes mime type and removes casing/parameters', () => {
    expect(normalizeMimeType(' Video/MP4 ; charset=utf-8 ')).toBe('video/mp4');
  });

  it('infers video mime from extension when mime is generic', () => {
    expect(resolvePreviewMimeType('application/octet-stream', 'demo.mkv')).toBe('video/x-matroska');
    expect(resolvePreviewMimeType('', 'demo.webm')).toBe('video/webm');
  });

  it('keeps explicit mime type when it is already concrete', () => {
    expect(resolvePreviewMimeType('video/mp4', 'demo.bin')).toBe('video/mp4');
  });

  it('falls back to octet-stream when extension is unknown', () => {
    expect(resolvePreviewMimeType('application/octet-stream', 'archive.unknownext')).toBe('application/octet-stream');
  });

  it('detects preview capability for mainstream types', () => {
    expect(getPreviewCapabilities('application/octet-stream', 'doc.pdf').isPdf).toBe(true);
    expect(getPreviewCapabilities('application/octet-stream', 'movie.mp4').isVideo).toBe(true);
    expect(getPreviewCapabilities('application/octet-stream', 'clip.m3u8').isHls).toBe(true);
    expect(getPreviewCapabilities('application/octet-stream', 'note.json').isText).toBe(true);
  });
});
