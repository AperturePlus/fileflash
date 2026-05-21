import { describe, expect, it } from 'vitest';
import { isArchiveFileName } from './archive';

describe('utils/archive', () => {
  it('detects supported archive suffixes for extract preview routing', () => {
    expect(isArchiveFileName('a.zip')).toBe(true);
    expect(isArchiveFileName('b.7z')).toBe(true);
    expect(isArchiveFileName('c.tar')).toBe(true);
    expect(isArchiveFileName('d.tar.gz')).toBe(true);
    expect(isArchiveFileName('e.tgz')).toBe(true);
    expect(isArchiveFileName('f.gz')).toBe(true);
  });

  it('is case-insensitive and trims whitespace', () => {
    expect(isArchiveFileName('  Demo.ZIP  ')).toBe(true);
    expect(isArchiveFileName('ARCHIVE.TAR.GZ')).toBe(true);
  });

  it('does not treat non-archive names as archive', () => {
    expect(isArchiveFileName('movie.mp4')).toBe(false);
    expect(isArchiveFileName('note.txt')).toBe(false);
    expect(isArchiveFileName('gzip')).toBe(false);
    expect(isArchiveFileName('')).toBe(false);
    expect(isArchiveFileName(undefined)).toBe(false);
    expect(isArchiveFileName(null)).toBe(false);
  });
});
