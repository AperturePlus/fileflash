import SparkMD5 from 'spark-md5';  

export const HASH_CHUNK_SIZE_DEFAULT = 2 * 1024 * 1024;
export const HASH_CHUNK_SIZE_LARGE_FILE = 16 * 1024 * 1024;

/**  
 * 进度回调函数的类型定义。  
 * @param percentage - 当前计算进度的百分比 (0-100)。  
 * @param currentChunk - 当前正在处理的切片序号 (从 1 开始)。  
 * @param totalChunks - 文件被分成的总切片数。  
 */  
export type HashProgressCallback = (progress: {  
  percentage: number;  
  currentChunk: number;  
  totalChunks: number;  
}) => void;  

function createAbortError(message: string): Error {
  if (typeof DOMException !== 'undefined') {
    return new DOMException(message, 'AbortError');
  }
  const error = new Error(message);
  error.name = 'AbortError';
  return error;
}

/**  
 * 以分片、增量的方式异步计算文件的 MD5 哈希值。  
 * 使用 spark-md5 库，性能优秀，适用于大文件秒传场景。  
 *   
 * @param file - 需要计算哈希值的 File 对象。  
 * @param onProgress - (可选) 一个回调函数，用于接收哈希计算的实时进度。  
 * @param chunkSize - (可选) 每个分片的大小（以字节为单位）。默认为 2MB。  
 *                    对于 MD5，较小的分片通常能更好地利用其速度优势。  
 * @returns 返回一个 Promise，最终 resolve 为文件的 16 字节十六进制哈希字符串。  
 */  
export function calculateFileHash(  
  file: File,  
  onProgress?: HashProgressCallback,  
  chunkSize: number = HASH_CHUNK_SIZE_DEFAULT,
  options: {
    signal?: AbortSignal;
  } = {},
): Promise<string> {  
  return new Promise((resolve, reject) => {  
    const signal = options.signal;
    if (signal?.aborted) {
      reject(createAbortError('Hash calculation canceled.'));
      return;
    }

    // 初始化 spark-md5 的 ArrayBuffer 实例，用于增量计算  
    const spark = new SparkMD5.ArrayBuffer();  
    
    // 计算文件总分片数  
    const totalChunks = Math.ceil(file.size / chunkSize);  
    let currentChunk = 0;  

    // 创建一个 FileReader 实例来读取文件内容  
    const reader = new FileReader();  
    let settled = false;

    const cleanupSignal = () => {
      if (signal) {
        signal.removeEventListener('abort', handleAbort);
      }
    };

    const fail = (error: Error) => {
      if (settled) return;
      settled = true;
      cleanupSignal();
      reject(error);
    };

    const succeed = (hash: string) => {
      if (settled) return;
      settled = true;
      cleanupSignal();
      resolve(hash);
    };

    function handleAbort() {
      if (settled) return;
      try {
        reader.abort();
      } catch {
        // Ignore FileReader abort errors during cancellation.
      }
      fail(createAbortError('Hash calculation canceled.'));
    }
    if (signal) {
      signal.addEventListener('abort', handleAbort, { once: true });
    }

    /**  
     * 加载下一个分片进行处理  
     */  
    function loadNext() {  
      if (signal?.aborted) {
        fail(createAbortError('Hash calculation canceled.'));
        return;
      }
      // 如果所有分片都已处理完毕  
      if (currentChunk >= totalChunks) {  
        // 完成哈希计算并返回十六进制结果  
        // 调用 end() 方法获取最终的 MD5 hash  
        succeed(spark.end());  
        return;  
      }  

      // 计算当前分片的起始和结束位置  
      const start = currentChunk * chunkSize;  
      const end = Math.min(start + chunkSize, file.size);  
      
      // 读取当前分片  
      reader.readAsArrayBuffer(file.slice(start, end));  
    }  

    // 当 FileReader 成功读取一个分片后触发  
    reader.onload = (e) => {  
      // 确保读取结果存在  
      if (!e.target?.result) {  
        fail(new Error('Failed to read file chunk.'));
        return;  
      }  

      try {  
        if (signal?.aborted) {
          fail(createAbortError('Hash calculation canceled.'));
          return;
        }
        // 将读取到的 ArrayBuffer 数据喂给哈希实例，使用append方法 
        spark.append(e.target.result as ArrayBuffer);  

        // 更新当前处理的切片计数  
        currentChunk++;  
        
        // 如果提供了进度回调，则调用它  
        if (onProgress) {  
          const percentage = Math.round((currentChunk / totalChunks) * 100);  
          onProgress({  
            percentage,  
            currentChunk,  
            totalChunks,  
          });  
        }  
        
        // 处理下一个分片  
        loadNext();  

      } catch (error) {  
        fail(error instanceof Error ? error : new Error(String(error)));  
      }  
    };  

    // 当 FileReader 读取出错时触发  
    reader.onerror = () => {  
      fail(new Error('An error occurred while reading the file.'));
    };  

    reader.onabort = () => {
      fail(createAbortError('Hash calculation canceled.'));
    };

    // 启动第一个分片的加载  
    loadNext();  
  });  
}  

export function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
}

export function fileToArrayBuffer(file: File): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}  
