import Mock from 'mockjs';
import { vfsApi } from '../vfs';
import JSZip from 'jszip';

// Helper to convert base64 to blob
function base64ToBlob(base64: string, type: string): Blob {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type });
}


export const setupFileMocks = () => {
  // Download File
  Mock.mock(/\/api\/v1\/files\/(.+)\/download/, 'get', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/(.+)\/download/) || [])[1];
    const file = vfsApi.get(fileId);

    if (!file || file.type !== 'file') {
      return {
        success: false,
        code: 404,
        message: 'File not found',
      };
    }
    
    // If the file has real content stored, decode and serve it
    if (file.content) {
      // We don't store mime type, so we use a generic one.
      // In a real backend, you'd store and retrieve the mime type.
      return base64ToBlob(file.content, file.mimeType || 'application/octet-stream');
    }

    // Fallback for files without stored content
    const content = `Mock content for ${file.name}`;
    const blob = new Blob([content], { type: 'application/octet-stream' });
    
    // Return the blob directly for download
    return blob;
  });

  // Preview File (similar to download for now)
  Mock.mock(/\/api\/v1\/files\/(.+)\/preview/, 'get', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/(.+)\/preview/) || [])[1];
    const file = vfsApi.get(fileId);

    if (!file || file.type !== 'file') {
      return { success: false, code: 404, message: 'File not found' };
    }
    
    if (file.content) {
      return base64ToBlob(file.content, file.mimeType || 'application/octet-stream');
    }

    const content = `Mock preview content for ${file.name}`;
    const blob = new Blob([content], { type: 'text/plain' });
    return blob;
  });

  // Batch Download Files as Zip
  Mock.mock(/\/api\/v1\/files\/batch-download/, 'post', async (options) => {
    const { fileIds } = JSON.parse(options.body);
    const zip = new JSZip();

    for (const fileId of fileIds) {
      const file = vfsApi.get(fileId);
      if (file && file.type === 'file') {
        // In a real scenario, you'd fetch file content. Here, we generate it.
        const fileContent = `Mock content for ${file.name}`;
        zip.file(file.name, fileContent);
      }
    }

    const zipBlob = await zip.generateAsync({ type: 'blob' });
    return zipBlob;
  });

  // Move File
  Mock.mock(/\/api\/v1\/files\/(.+)\/move/, 'patch', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/(.+)\/move/) || [])[1];
    const { targetFolderId } = JSON.parse(options.body);
    const movedFile = vfsApi.move(fileId, targetFolderId);
    return { success: true, code: 200, data: movedFile };
  });

  // Rename File
  Mock.mock(/\/api\/v1\/files\/(?![^/]+\/(?:move|copy|download|preview|thumbnail)$)[^/]+$/, 'patch', (options) => {
    const fileId = options.url.match(/\/api\/v1\/files\/(.+)/)![1];
    const { fileName } = JSON.parse(options.body);
    const updatedFile = vfsApi.rename(fileId, fileName);
    return { success: true, code: 200, data: updatedFile };
  });

  // Delete File
  Mock.mock(/\/api\/v1\/files\/(.+)/, 'delete', (options) => {
    const fileId = (options.url.match(/\/api\/v1\/files\/(.+)/) || [])[1];
    vfsApi.delete(fileId);
    return { success: true, code: 200, data: { fileId, message: 'File moved to trash.' } };
  });

  // Batch Delete Files
  Mock.mock(/\/api\/v1\/files\/batch/, 'post', (options) => {
    const { action, fileIds, targetFolderId } = JSON.parse(options.body);
    if (action === 'delete') {
      fileIds.forEach((id: string) => vfsApi.delete(id));
      return { success: true, code: 200, data: { successCount: fileIds.length } };
    }
    if (action === 'move') {
      fileIds.forEach((id: string) => vfsApi.move(id, targetFolderId));
      return { success: true, code: 200, data: { successCount: fileIds.length } };
    }
    return { success: false, code: 400, message: 'Action not mocked' };
  });
}; 