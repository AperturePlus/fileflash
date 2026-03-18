import Mock from 'mockjs';
import { vfsApi } from '../vfs';
import { arrayBufferToBase64, fileToArrayBuffer } from '../../utils/hash';

export const setupUploadMocks = () => {
  // Store chunks temporarily. In a real scenario, this would be on a server.
  const chunkStorage = new Map<string, Map<number, File>>();

  // Preflight Upload
  Mock.mock(/\/api\/v1\/uploads\/preflight/, 'post', (options) => {
    const uploadId = Mock.Random.guid();
    chunkStorage.set(uploadId, new Map());
    return {
      success: true, code: 200, message: 'Ready for upload.',
      data: {
        status: 'UPLOADING',
        uploadId: uploadId,
        chunkSize: 5 * 1024 * 1024, // 5MB chunks
        uploadedChunkIndexes: [],
      }
    };
  });

  // Upload Chunk
  Mock.mock(/\/api\/v1\/uploads\/(.+)\/chunk/, 'post', (options) => {
    const uploadId = (options.url.match(/\/api\/v1\/uploads\/(.+)\/chunk/) || [])[1];
    const formData = options.body as FormData; // Mockjs passes FormData directly
    const chunk = formData.get('chunk') as File;
    const chunkIndex = parseInt(formData.get('chunkIndex') as string, 10);
    
    if (chunkStorage.has(uploadId)) {
      chunkStorage.get(uploadId)!.set(chunkIndex, chunk);
      return { success: true, code: 200, message: `Chunk ${chunkIndex} uploaded for ${uploadId}.`};
    } else {
      return { success: false, code: 404, message: 'Upload ID not found.' };
    }
  });

  // Merge Chunks
  Mock.mock(/\/api\/v1\/uploads\/(.+)\/merge/, 'post', (options) => {
    const uploadId = (options.url.match(/\/api\/v1\/uploads\/(.+)\/merge/) || [])[1];
    const { fileName, parentId, mimeType } = JSON.parse(options.body);

    if (!chunkStorage.has(uploadId)) {
      return { success: false, code: 404, message: 'Upload ID not found.' };
    }

    const chunksMap = chunkStorage.get(uploadId)!;
    const sortedChunks = Array.from(chunksMap.keys()).sort((a, b) => a - b).map(key => chunksMap.get(key)!);
    
    if (sortedChunks.length === 0) {
       return { success: false, code: 400, message: 'No chunks found for this upload.' };
    }

    const completeFileBlob = new Blob(sortedChunks);
    
    const newFileVfsNode = vfsApi.createFile(parentId, fileName, completeFileBlob.size, mimeType || 'application/octet-stream');
    
    chunkStorage.delete(uploadId); // Clean up after merge

    // The mock must return a response that matches the `MergeChunksResponse` type definition
    const responseData = {
      fileId: newFileVfsNode.id,
      fileName: newFileVfsNode.name,
      fileSize: newFileVfsNode.size || 0,
      mimeType: newFileVfsNode.mimeType || 'application/octet-stream',
      folderId: newFileVfsNode.parent || 'root',
      objectHash: `mock-hash-${newFileVfsNode.id}`,
      createdAt: newFileVfsNode.createdAt,
      downloadUrl: `/api/v1/files/${newFileVfsNode.id}/download`,
    };

    return {
      success: true,
      code: 201,
      message: 'File created successfully.',
      data: responseData,
    };
  });
}; 