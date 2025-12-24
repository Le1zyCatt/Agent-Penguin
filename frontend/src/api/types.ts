export interface Contact {
  id?: string;
  name?: string;
  nickname?: string;
  group_name?: string;
  type?: 'group' | 'private' | string;
  [key: string]: any;
}

export interface DocItem {
  file_name: string;
  file_path: string;
  time?: string;
  extracted_content?: string;
  sender?: string;
  size?: number;
  [key: string]: any;
}

export interface ImageItem {
  file_name: string;
  file_path: string;
  time?: string;
  sender?: string;
  ocr_preview?: string;
  [key: string]: any;
}

export interface VectorDBList {
  success: boolean;
  databases: string[];
  current_db?: string;
}

export interface ChatHistoryItem {
  id: string;
  name: string;
  group_name?: string;
  time: string;
  text: string;
  content_type: string;
  extracted_content?: string;
  local_path?: string;
  msgtype?: string;
}

export interface ReplySettingResponse {
  success: boolean;
  enabled?: boolean;
  settings?: Record<string, boolean>;
  [key: string]: any;
}
