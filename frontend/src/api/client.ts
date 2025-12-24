import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export const api = axios.create({
  baseURL,
  timeout: 120000, // 增加到 120 秒，以处理长时间的 AI 调用
});

export const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
};
