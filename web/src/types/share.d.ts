/**
 * 分享设置
 * @property {boolean} passwordProtected - 是否密码保护
 * @property {string | null} expireAt - 过期时间
 * @property {boolean} allowDownload - 是否允许下载
 * @property {boolean} allowPreview - 是否允许预览
 */
export interface ShareSettings {
    passwordProtected: boolean;
    expireAt: string | null;
    allowDownload: boolean;
    allowPreview: boolean;
  }
  
  /**
   * 分享项中的文件/文件夹信息
   * @property {string} id - 分享项ID
   * @property {string} name - 分享项名称
   * @property {number} size - 分享项大小
   * @property {string} mimeType - 分享项MIME类型
   * @property {string} folderPath - 分享项文件夹路径
   */
  export interface SharedItemInfo {
    id: string;
    name: string;
    size: number;
    mimeType: string;
    folderPath?: string; // 在列表中可能存在
  }
  
  /**
   * 分享链接对象 (用于列表和详情)
   * @property {string} shareId - 分享ID
   * @property {string} shareLink - 分享链接
   * @property {string} itemType - 分享项类型
   * @property {SharedItemInfo} itemInfo - 分享项信息
   * @property {ShareSettings} settings - 分享设置
   * @property {string} createdAt - 创建时间
   */
  export interface Share {
    shareId: string;
    shareLink: string;
    itemType: 'file' | 'folder';
    itemInfo: SharedItemInfo;
    settings: ShareSettings;
    createdAt: string;
    visitCount?: number;
    downloadCount?: number;
  }
  
  /**
   * 访问分享链接成功后的响应数据 (POST /shares/{share_id}/access)
   * @property {string} accessToken - 访问令牌
   * @property {number} expiresIn - 过期时间
   * @property {string} itemType - 分享项类型
   * @property {SharedItemInfo} itemInfo - 分享项信息
   * @property {AccessUrls} accessUrls - 访问链接
   */
  export interface AccessShareResponseData {
    accessToken: string;
    expiresIn: number;
    itemType: 'file' | 'folder';
    itemInfo: SharedItemInfo;
    accessUrls: {
      download: string;
      preview: string;
    };
  }

/**
 * 创建分享链接的请求体
 */
export interface CreateShareRequest {
  resourceType: 'file' | 'folder';
  resourceId: string;
}

/**
 * 分享响应数据
 */
export interface CreateShareResponse {
  shareId: string;
  shareCode: string;
  shareLink: string;
}

/**
 * 访问分享内容的请求体
 */
export interface AccessShareRequest {
  password?: string;
}

/**
 * 协作者类型，用于在分享对话框中统一表示用户和用户组
 * @property {string} id - 用户或用户组的唯一ID
 * @property {string} name - 用户名或用户组名
 * @property {'user' | 'group'} type - 协作者类型
 * @property {string} [email] - 用户的邮箱 (可选)
 * @property {'read' | 'write' | 'admin'} [permission] - 协作者的权限 (可选)
 * @property {string} [permissionId] - 权限ID，用于更新和删除权限 (可选)
 */
export interface Collaborator {
  id: string;
  name: string;
  type: 'user' | 'group';
  email?: string;
  avatar?: string; // Optional avatar URL
  permission?: 'read' | 'write' | 'admin';
  permissionId?: string;
}

/**
 * "与我共享"列表中的项目类型
 * @property {'file' | 'folder'} itemType - 项目类型
 * @property {string} id - 文件或文件夹的ID
 * @property {string} name - 文件或文件夹的名称
 * @property {number} size - 项目大小 (字节)
 * @property {string} [mimeType] - 文件的MIME类型
 * @property {string} sharedBy - 分享者的用户名
 * @property {'read' | 'write'} permission - 当前用户的权限
 * @property {string} sharedAt - 分享时间
 */
export interface SharedItem {
  itemType: 'file' | 'folder';
  id: string;
  name: string;
  size: number;
  mimeType?: string;
  sharedBy: string;
  permission: 'read' | 'write';
  sharedAt: string;
}

export interface GetSharedItemsRequest {
  page?: number;
  perPage?: number;
  sort?: 'name' | 'size' | 'sharedAt' | 'sharedBy';
  order?: 'asc' | 'desc';
}