import { api } from './client';
import type { Contact, DocItem, ImageItem, VectorDBList, ReplySettingResponse } from './types';

export const fetchContacts = async (typeFilter?: string) => {
  const res = await api.get('/api/msg/list', { params: { type_filter: typeFilter } });
  return res.data?.data as Contact[] || [];
};

export const searchChat = async (contact: string, query: string, k = 10) => {
  const res = await api.get('/api/chat/search', { params: { contact, query, k } });
  return res.data?.results ?? [];
};

export const summarizeChat = async (contact_id: string, limit = 100, target_lang = 'Chinese') => {
  const form = new FormData();
  form.append('contact_id', contact_id);
  form.append('limit', String(limit));
  form.append('target_lang', target_lang);
  const res = await api.post('/api/msg/summarize', form);
  return res.data;
};

export const notifyChat = async (contact_id: string, limit = 100) => {
  const form = new FormData();
  form.append('contact_id', contact_id);
  form.append('limit', String(limit));
  const res = await api.post('/api/msg/notification', form);
  return res.data;
};

export const fetchDocs = async (contact_id: string) => {
  const res = await api.get('/api/doc/list', { params: { contact_id } });
  return res.data?.data as DocItem[] || [];
};

export const summarizeDocs = async (contact_id: string, limit = 5, target_lang = 'Chinese') => {
  const form = new FormData();
  form.append('contact_id', contact_id);
  form.append('limit', String(limit));
  form.append('target_lang', target_lang);
  const res = await api.post('/api/doc/summarize', form);
  return res.data;
};

export const translateDoc = async (file_path: string, target_lang = 'Chinese') => {
  const form = new FormData();
  form.append('file_path', file_path);
  form.append('target_lang', target_lang);
  const res = await api.post('/api/doc/translate', form, { responseType: 'blob' });
  return res;
};

export const fetchImages = async (contact_id: string) => {
  const res = await api.get('/api/image/list', { params: { contact_id } });
  return res.data?.data as ImageItem[] || [];
};

export const translateImage = async (file_path: string, target_lang = 'Chinese') => {
  const form = new FormData();
  form.append('file_path', file_path);
  form.append('target_lang', target_lang);
  const res = await api.post('/api/image/translate', form, { responseType: 'blob' });
  return res;
};

export const getReplySetting = async (contact_id: string) => {
  const res = await api.get<ReplySettingResponse>('/api/reply/settings', { params: { contact_id } });
  return res.data;
};

export const updateReplySetting = async (contact_id: string, enabled: boolean) => {
  const form = new FormData();
  form.append('contact_id', contact_id);
  form.append('enabled', String(enabled));
  const res = await api.post('/api/reply/settings', form);
  return res.data as ReplySettingResponse;
};

export const listReplySettings = async () => {
  const res = await api.get<ReplySettingResponse>('/api/reply/settings');
  return res.data;
};

export const listVectorDBs = async () => {
  const res = await api.get<VectorDBList>('/api/vector-db/list');
  return res.data;
};

export const switchVectorDB = async (db_path: string) => {
  const form = new FormData();
  form.append('db_path', db_path);
  const res = await api.post('/api/vector-db/switch', form);
  return res.data;
};

export const getCurrentVectorDB = async () => {
  const res = await api.get('/api/vector-db/current');
  return res.data;
};

export const sendTestMessage = async (params: {
  contact_id: string;
  message_type: 'group' | 'private';
  raw_message: string;
  is_at?: boolean;
}) => {
  const { contact_id, message_type, raw_message, is_at } = params;
  const payload =
    message_type === 'group'
      ? {
          post_type: 'message',
          message_type,
          group_id: contact_id,
          user_id: contact_id,
          group_name: 'Test Group',
          message_id: Date.now(),
          raw_message,
          is_at: !!is_at,
          sender: { nickname: 'FrontEnd Tester' },
          time: Math.floor(Date.now() / 1000),
        }
      : {
          post_type: 'message',
          message_type,
          user_id: contact_id,
          message_id: Date.now(),
          raw_message,
          is_at: !!is_at,
          sender: { nickname: 'FrontEnd Tester' },
          time: Math.floor(Date.now() / 1000),
        };
  const res = await api.post('/api/message/save', payload);
  return res.data;
};
