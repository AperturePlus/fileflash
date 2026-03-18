/**
 * 文件项的基础结构
 */
export interface FileItem {
    itemType: 'file';
    id: string;
    name: string;
    size: number;
    mimeType: string;
    ownerName: string;
    updatedAt: string;
    createdAt: string;
    folderId: string;
    permission?: 'read' | 'write' | 'owner';
  }
  
  /**
   * 文件夹项的基础结构
   */
  export interface FolderItem {
    itemType: 'folder';
    id: string;
    name: string;
    size: number; // 文件夹大小
    ownerName: string;
    updatedAt: string;
    createdAt: string;
    parentFolderId: string | null;
    permission?: 'read' | 'write' | 'owner';
  }
  
  /**
   * 文件夹内容项 (文件或文件夹的联合类型)
   * 用于 GET /folders/{folderId}/contents
   */
  export type ContentItem = FileItem | FolderItem;

  /**
   * 获取文件夹内容的请求参数
   */
  export interface GetFolderContentsRequest {
    folderId: string;
    page?: number;
    perPage?: number;
    sort?: 'name' | 'size' | 'createdAt' | 'updatedAt';
    order?: 'asc' | 'desc';
    search?: string;
  }
  
  /**
   * 文件夹路径中的单个路径项
   */
  export interface PathItem {
    folderId: string | null; // 根目录为 null
    name: string;
  }
  
  /**
   * 文件夹完整路径的响应数据 (GET /folders/{folderId}/path)
   */
  export interface FolderPathResponse {
    fullPath: string;
    pathItems: PathItem[];
  }

  /**
   * 创建文件夹的请求体
   */
  export interface CreateFolderRequest {
    folderName: string;
    parentFolderId: string | null;
  }

  /**
   * 重命名文件夹的请求体
   */
  export interface RenameFolderRequest {
    folderName: string;
  }

  /**
   * 移动文件夹的请求体
   */
  export interface MoveFolderRequest {
    targetParentId: string;
  }

  /**
 * 回收站中的项目
 * @property {string} itemType - 项目类型
 * @property {string} id - 项目ID
 * @property {string} name - 项目名称
 * @property {string} originalPath - 原始路径
 * @property {number} size - 项目大小
 * @property {string} mimeType - 项目MIME类型
 * @property {string} deletedAt - 删除时间
 */
export interface RecycleBinItem {
  itemType: 'file' | 'folder';
  id: string;
  name: string;
  originalPath: string;
  size: number;
  mimeType?: string; // 文件夹没有 mime_type
  deletedAt: string;
  autoDeleteAt: string;
  daysUntilPermanentDelete: number;
  canRestore: boolean;
  restoreConflicts: boolean;
}

// --- 文件上传相关类型 ---

/**
 * 文件上传预检请求 (POST /uploads/preflight)
 * 在真正上传文件前，客户端首先发送此请求，将文件的基本元数据提交给服务器。
 * 服务器根据这些信息判断是否可以秒传、是否需要分片上传，并返回相应的指令。
 */
export interface UploadPreflightRequest {
  /**
   * 文件的完整哈希值 (例如，由 spark-md5 计算出的 32 位字符串)。
   * @example "d41d8cd98f00b204e9800998ecf8427e"
   */
  fileHash: string;

  /**
   * 用户上传时的原始文件名，包含扩展名。
   * @example "我的家庭照片.jpg"
   */
  fileName: string;

  /**
   * 文件的总大小，以字节为单位。
   * @example 10485760
   */
  fileSize: number;

  /**
   * 文件的 MIME 类型 (例如 'image/jpeg', 'video/mp4')。
   * @example "image/jpeg"
   */
  mimeType: string;

  /**
   * 用户希望将文件上传到哪个目录下。
   * @example "folder_id_12345"
   */
  parentId: string; 
}

/**
 * 文件上传预检响应
 * @property {string} status - 上传状态
 * @property {string} fileId - 文件ID
 * @property {string} uploadId - 上传ID
 * @property {number} chunkSize - 分片大小
 * @property {number[]} uploadedChunkIndexes - 已上传分片索引
 */
export interface UploadPreflightResponse {
  /**
   * 明确告知前端下一步的状态。
   * - 'COMPLETE': 秒传成功，上传流程结束。
   * - 'UPLOADING': 文件需要上传，请根据后续字段开始或继续上传。
   */
  status: 'COMPLETE' | 'UPLOADING';

  /**
   * 文件的最终唯一标识符。
   * 仅在 status 为 'COMPLETE' 时提供。
   * @example "file_id_abcde"
   */
  fileId?: string;

  /**
   * 后端为此文件创建的唯一上传会话 ID。
   * 在后续所有分片上传请求中都必须携带此 ID。
   * 仅在 status 为 'UPLOADING' 时提供。
   * @example "upload_session_fghij"
   */
  uploadId?: string;

  /**
   * 后端期望每个分片的大小（字节）。
   * 前端应遵循此大小进行切片，以确保后端能正确合并。
   * 仅在 status 为 'UPLOADING' 时提供。
   * @example 5242880 (5 MB)
   */
  chunkSize?: number;

  /**
   * 一个数组，包含了后端已经成功接收并保存的分片序号（从 0 开始）。
   * 用于断点续传。
   * 仅在 status 为 'UPLOADING' 时提供。
   */
  uploadedChunkIndexes?: number[];
}


/**
 * 发起合并分片请求的负载 (POST /uploads/{uploadId}/merge)
 * 当所有分片都上传成功后，发送此请求通知后端将所有分片合并成一个完整的文件。
 */
export interface MergeChunksRequest {
  /**
   * 完整文件的哈希值，用于后端最终校验。
   */
  fileHash: string;

  /**
   * 文件的原始文件名。
   */
  fileName: string;
  
  /**
   * 文件的 MIME 类型。
   */
  mimeType: string;

  /**
   * 目标父文件夹ID。
   */
  parentId: string;
}

/**
 * 分片合并成功后的响应数据，代表一个常规上传的完成。
 * 其结构与秒传成功后，在 Preflight 响应中直接返回的文件信息类似。
 * @property {string} fileId - 文件ID
 * @property {string} fileName - 文件名
 * @property {number} fileSize - 文件大小
 * @property {string} mimeType - 文件MIME类型
 * @property {string} folderId - 父文件夹ID
 * @property {string} objectHash - 文件哈希值
 * @property {string} createdAt - 创建时间
 */
export interface MergeChunksResponse {
  fileId: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  folderId: string;
  objectHash: string;
  createdAt: string;
  downloadUrl: string;
}

/**
 * 获取文件列表的查询参数
 */
export interface GetFilesRequest {
  folderId?: string;
  page?: number;
  perPage?: number;
  sort?: 'name' | 'size' | 'createdAt' | 'updatedAt';
  order?: 'asc' | 'desc';
  search?: string;
  mimeType?: string;
}

/**
 * 文件详情
 */
export interface FileDetails extends FileItem {
  status: boolean;
  updatedAt: string;
}

/**
 * 重命名文件的请求体
 */
export interface RenameFileRequest {
  fileName: string;
}

/**
 * 移动文件的请求体
 */
export interface MoveFileRequest {
  targetFolderId: string;
}

/**
 * 复制文件的请求体
 */
export interface CopyFileRequest {
  targetFolderId: string;
  newName?: string;
}

/**
 * 批量操作文件的请求体
 */
export interface BatchFilesRequest {
  action: 'delete' | 'move' | 'copy';
  fileIds: string[]; // 修改为 string[] 以保持一致性
  targetFolderId?: string; // 修改为 string 以保持一致性
}

/**
 * 回收站项目 (改进以匹配文档)
 */
export interface RecycleBinItem {
  itemType: 'file' | 'folder';
  id: string;
  name: string;
  originalPath: string;
  size: number;
  mimeType?: string;
  folderId?: string;
  folderName?: string;
  deletedAt: string;
  autoDeleteAt: string;
  daysUntilPermanentDelete: number;
  canRestore: boolean;
  restoreConflicts: boolean;
}

/**
 * 恢复回收站项目的请求体
 */
export interface RestoreRecycleItemRequest {
  itemType: 'file' | 'folder';
  targetFolderId?: string;
}

/**
 * 获取回收站内容的查询参数
 */
export interface GetRecycleBinRequest {
  page?: number;
  perPage?: number;
  itemType?: 'file' | 'folder';
}