import { describe, expect, it } from 'vitest';
import { mount } from '../../../test/mount';
import FileRow from './FileRow.vue';

describe('FileRow media optimization label', () => {
  it('renders processing label for queued optimization status', () => {
    const wrapper = mount(FileRow as any, {
      props: {
        item: {
          itemType: 'file',
          id: 'f1',
          name: 'video.mp4',
          size: 1024,
          mimeType: 'video/mp4',
          ownerName: 'owner',
          updatedAt: '2026-05-12T00:00:00Z',
          createdAt: '2026-05-12T00:00:00Z',
          folderId: 'root',
          mediaOptimization: {
            status: 'queued',
            mediaType: 'video',
            updatedAt: '2026-05-12T00:00:00Z',
          },
        },
        selected: false,
        renaming: false,
        renameValue: '',
      },
    });

    expect(wrapper.text()).toContain('处理中');
  });
});

