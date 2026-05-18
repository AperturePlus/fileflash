const ARCHIVE_EXTENSIONS = ['.zip', '.7z', '.tar.gz', '.tgz', '.tar', '.gz'] as const;

export function isArchiveFileName(fileName: string | undefined | null): boolean {
  const normalized = (fileName || '').trim().toLowerCase();
  if (!normalized) {
    return false;
  }
  return ARCHIVE_EXTENSIONS.some((ext) => normalized.endsWith(ext));
}
