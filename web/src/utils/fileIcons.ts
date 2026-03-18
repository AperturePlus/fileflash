import codeIcon from '../assets/code.svg';
import compressedIcon from '../assets/compressed.svg';
import executableIcon from '../assets/executable.svg';
import imageIcon from '../assets/image.svg';
import genericFileIcon from '../assets/generic/file.svg';
import pdfIcon from '../assets/pdf.svg';
import configIcon from '../assets/config.svg';
import videoIcon from '../assets/video.svg';
import audioIcon from '../assets/audio.svg';

const extensionMap: Record<string, string> = {
    // Code
    'js': codeIcon,
    'ts': codeIcon,
    'html': codeIcon,
    'css': codeIcon,
    'json': codeIcon,
    'py': codeIcon,
    'java': codeIcon,
    'cpp': codeIcon,
    'c': codeIcon,
    'cs': codeIcon,
    'go': codeIcon,
    'php': codeIcon,
    'rb': codeIcon,
    'swift': codeIcon,
    'sql': codeIcon,
    // PDF
    'pdf': pdfIcon,
    // Compressed
    'zip': compressedIcon,
    'rar': compressedIcon,
    '7z': compressedIcon,
    'gz': compressedIcon,
    'tar': compressedIcon,
    // Executable
    'exe': executableIcon,
    'sh': executableIcon,
    'bat': executableIcon,
    // Image
    'jpg': imageIcon,
    'jpeg': imageIcon,
    'png': imageIcon,
    'gif': imageIcon,
    'svg': imageIcon,
    'webp': imageIcon,
    'bmp': imageIcon,
    // Generic
    'txt': genericFileIcon,
    'md': genericFileIcon,
    'log': genericFileIcon,
    //config
    'ini': configIcon,
    'conf': configIcon,
    'cfg': configIcon,
    'xml': configIcon,
    'yaml': configIcon,
    'yml': configIcon,
    //video
    'mp4': videoIcon,
    'mov': videoIcon,
    'avi': videoIcon,
    'mkv': videoIcon,
    'wmv': videoIcon,
    'flv': videoIcon,
    'webm': videoIcon,
    //audio
    'mp3': audioIcon,
    'wav': audioIcon,
    'ogg': audioIcon,
    'm4a': audioIcon,
    'aac': audioIcon,
    'flac': audioIcon,
    'wma': audioIcon,
};

export function getIconForFile(fileName: string): string {
  const extension = fileName.split('.').pop()?.toLowerCase();
  if (extension && extensionMap[extension]) {
    return extensionMap[extension];
  }
  return genericFileIcon;
} 