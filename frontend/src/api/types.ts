export interface Contact {
  id?: string;
  name?: string;
  nickname?: string;
  group_name?: string;
  type?: 'group' | 'private' | string;
  [key: string]: any;
}

export interface DocItem {
  name: string;
  path: string;
  time?: string;
  extracted_content?: string;
  [key: string]: any;
}

export interface ImageItem {
  name: string;
  path: string;
  time?: string;
  [key: string]: any;
}

export interface VectorDBList {
  success: boolean;
  databases: string[];
  current_db?: string;
}

export interface ReplySettingResponse {
  success: boolean;
  enabled?: boolean;
  settings?: Record<string, boolean>;
  [key: string]: any;
}
