const GENERIC_MIME_TYPES = new Set([
  '',
  'application/octet-stream',
  'binary/octet-stream',
]);

const EXTENSION_MIME_MAP: Record<string, string> = {
  pdf: 'application/pdf',
  txt: 'text/plain',
  md: 'text/markdown',
  csv: 'text/csv',
  log: 'text/plain',
  json: 'application/json',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  gif: 'image/gif',
  webp: 'image/webp',
  bmp: 'image/bmp',
  svg: 'image/svg+xml',
  mp3: 'audio/mpeg',
  wav: 'audio/wav',
  ogg: 'audio/ogg',
  m4a: 'audio/mp4',
  aac: 'audio/aac',
  flac: 'audio/flac',
  wma: 'audio/x-ms-wma',
  mp4: 'video/mp4',
  m4v: 'video/x-m4v',
  mov: 'video/quicktime',
  mkv: 'video/x-matroska',
  webm: 'video/webm',
  avi: 'video/x-msvideo',
  wmv: 'video/x-ms-wmv',
  flv: 'video/x-flv',
  m3u8: 'application/vnd.apple.mpegurl',
};

const TEXT_EXTENSIONS = new Set(['txt', 'md', 'csv', 'log', 'json', 'xml', 'yaml', 'yml']);
const HLS_MIME_TYPES = new Set(['application/vnd.apple.mpegurl', 'application/x-mpegurl']);

function inferMimeTypeByExtension(extension: string): string {
  return EXTENSION_MIME_MAP[extension] || 'application/octet-stream';
}

export function normalizeMimeType(mimeType: string | undefined | null): string {
  const normalized = (mimeType || '')
    .trim()
    .toLowerCase()
    .split(';', 1)[0]
    .trim();
  return normalized || 'application/octet-stream';
}

export function extractFileExtension(fileName: string | undefined | null): string {
  const normalized = (fileName || '').trim().toLowerCase();
  const dotIndex = normalized.lastIndexOf('.');
  if (dotIndex <= 0 || dotIndex === normalized.length - 1) {
    return '';
  }
  return normalized.slice(dotIndex + 1);
}

export function resolvePreviewMimeType(
  mimeType: string | undefined | null,
  fileName: string | undefined | null,
): string {
  const normalizedMimeType = normalizeMimeType(mimeType);
  if (!GENERIC_MIME_TYPES.has(normalizedMimeType)) {
    return normalizedMimeType;
  }
  const extension = extractFileExtension(fileName);
  return inferMimeTypeByExtension(extension);
}

export interface PreviewCapabilities {
  extension: string;
  mimeType: string;
  isText: boolean;
  isPdf: boolean;
  isImage: boolean;
  isAudio: boolean;
  isVideo: boolean;
  isHls: boolean;
  isSupported: boolean;
}

export function getPreviewCapabilities(
  mimeType: string | undefined | null,
  fileName: string | undefined | null,
): PreviewCapabilities {
  const extension = extractFileExtension(fileName);
  const resolvedMimeType = resolvePreviewMimeType(mimeType, fileName);
  const isHls = HLS_MIME_TYPES.has(resolvedMimeType) || extension === 'm3u8';
  const isPdf = resolvedMimeType === 'application/pdf' || extension === 'pdf';
  const isImage = resolvedMimeType.startsWith('image/');
  const isAudio = resolvedMimeType.startsWith('audio/');
  const isVideo = resolvedMimeType.startsWith('video/') || isHls;
  const isText = resolvedMimeType.startsWith('text/')
    || resolvedMimeType.includes('json')
    || TEXT_EXTENSIONS.has(extension);

  return {
    extension,
    mimeType: resolvedMimeType,
    isText,
    isPdf,
    isImage,
    isAudio,
    isVideo,
    isHls,
    isSupported: isText || isPdf || isImage || isAudio || isVideo,
  };
}
