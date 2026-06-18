import { api } from './client';

export async function fetchKnowledgeFiles() {
  return api.get('/knowledge-base/files');
}

export async function uploadKnowledgeFile(file) {
  if (!file.name.toLowerCase().endsWith('.txt')) {
    throw new Error('仅允许上传 .txt 文件');
  }
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/knowledge-base/upload', formData);
}

export async function deleteKnowledgeFile(id) {
  return await api.delete(`/knowledge-base/files/${id}`);
}

export async function retryIndexFile(id) {
  return api.post(`/knowledge-base/files/${id}/retry`);
}
