import { ref } from 'vue';
import mitt from 'mitt';

type Events = {
  'move-items': { 
    sourceItemIds: string[];
    targetFolderId: string;
    targetFolderName: string;
  };
  'refresh-file-tree': void;
  'search-files': { query: string };
};

export const eventBus = mitt<Events>(); 