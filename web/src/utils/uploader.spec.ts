import { AxiosError } from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HASH_CHUNK_SIZE_LARGE_FILE } from './hash';

const postMock = vi.fn();
const getMock = vi.fn();
const calculateFileHashMock = vi.fn();

vi.mock('./http', () => ({
  default: {
    post: (...args: unknown[]) => postMock(...args),
    get: (...args: unknown[]) => getMock(...args),
  },
}));

vi.mock('./hash', async () => {
  const actual = await vi.importActual<typeof import('./hash')>('./hash');
  return {
    ...actual,
    calculateFileHash: (...args: unknown[]) => calculateFileHashMock(...args),
  };
});

import { uploadFile } from './uploader';

function makePreflightError(message: string): AxiosError {
  return new AxiosError(
    message,
    'ERR_BAD_REQUEST',
    { headers: {} } as any,
    undefined,
    {
      status: 413,
      statusText: 'Request Entity Too Large',
      headers: {},
      config: { headers: {} } as any,
      data: { message },
    } as any,
  );
}

describe('utils/uploader', () => {
  beforeEach(() => {
    postMock.mockReset();
    getMock.mockReset();
    calculateFileHashMock.mockReset();
    calculateFileHashMock.mockResolvedValue('a'.repeat(64));
  });

  it('uses backend preflight error message when preflight fails', async () => {
    postMock.mockRejectedValueOnce(makePreflightError('File size exceeds maximum upload limit'));

    await expect(
      uploadFile({
        file: new File(['x'], 'large.bin', { type: 'application/octet-stream' }),
        parentId: 'root',
      }),
    ).rejects.toThrow('File size exceeds maximum upload limit');
  });

  it('uses larger chunks for hash computation than upload chunks', async () => {
    postMock.mockResolvedValueOnce({
      status: 'COMPLETE',
      fileId: 'file-1',
    });

    await uploadFile({
      file: new File(['hello'], 'demo.txt', { type: 'text/plain' }),
      parentId: 'root',
      chunkSize: 5 * 1024 * 1024,
    });

    expect(calculateFileHashMock).toHaveBeenCalledTimes(1);
    expect(calculateFileHashMock.mock.calls[0]?.[2]).toBe(HASH_CHUNK_SIZE_LARGE_FILE);
  });
});
