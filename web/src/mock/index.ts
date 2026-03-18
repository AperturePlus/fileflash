import { setupAuthMocks } from './handlers/auth';
import { setupFolderMocks } from './handlers/folder';
import { setupFileMocks } from './handlers/file';
import { setupUploadMocks } from './handlers/upload';
import { setupUserMocks } from './handlers/user';
import { setupUserGroupMocks } from './handlers/usergroup';
import { setupShareMocks } from './handlers/share';
import { setupRecycleMocks } from './handlers/recycle';

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
};

// Immediately setup mocks when this module is imported
setupMocks(); 