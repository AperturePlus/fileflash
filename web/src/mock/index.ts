import { setupAuthMocks } from './handlers/auth';
import { setupFolderMocks } from './handlers/folder';
import { setupFileMocks } from './handlers/file';
import { setupUploadMocks } from './handlers/upload';
import { setupUserMocks } from './handlers/user';
import { setupUserGroupMocks } from './handlers/usergroup';
import { setupShareMocks } from './handlers/share';
import { setupRecycleMocks } from './handlers/recycle';
import { setupPermissionMocks } from './handlers/permission';
import { setupNotificationMocks } from './handlers/notification';
import { setupLogMocks } from './handlers/log';
import { setupStorageMocks } from './handlers/storage';
import { setupSystemMocks } from './handlers/system';
import { setupJobsMocks } from './handlers/jobs';
import { setupSkillMocks } from './handlers/skill';
import { setupAgentMocks } from './handlers/agent';

// Setup all mock handlers
export const setupMocks = () => {
  setupAuthMocks();
  setupFolderMocks();
  setupFileMocks();
  setupUploadMocks();
  setupUserMocks();
  setupUserGroupMocks();
  setupShareMocks();
  setupRecycleMocks();
  setupPermissionMocks();
  setupNotificationMocks();
  setupLogMocks();
  setupStorageMocks();
  setupSystemMocks();
  setupJobsMocks();
  setupSkillMocks();
  setupAgentMocks();
};

// Immediately setup mocks when this module is imported
setupMocks(); 
