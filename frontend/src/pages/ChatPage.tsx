import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchContacts,
  searchChat,
  summarizeChat,
  notifyChat,
  getReplySetting,
  updateReplySetting,
  listVectorDBs,
  switchVectorDB,
  sendTestMessage,
} from '../api/endpoints';
import type { Contact } from '../api/types';
import Modal from '../components/Modal';
import { useToast } from '../components/ToastProvider';

const getContactId = (c: Contact): string => {
  return (
    c.id ||
    (c as any).contact_id ||
    (c as any).group_id ||
    (c as any).user_id ||
    c.name ||
    c.nickname ||
    c.group_name ||
    ''
  ).toString();
};

const getContactLabel = (c: Contact): string => {
  const name = c.name || c.nickname || c.group_name || getContactId(c);
  const type = c.type ? c.type.toUpperCase() : '';
  return `${name}${type ? ` · ${type}` : ''}`;
};

const ChatPage = () => {
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [selectedContact, setSelectedContact] = useState<string>('');
  const [keyword, setKeyword] = useState('');
  const [kValue, setKValue] = useState(10);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryText, setSummaryText] = useState('');
  const [notifyOpen, setNotifyOpen] = useState(false);
  const [notifyList, setNotifyList] = useState<any[]>([]);
  const [testMsg, setTestMsg] = useState('');
  const [messageType, setMessageType] = useState<'group' | 'private'>('group');

  const toast = useToast();
  const queryClient = useQueryClient();

  const contactsQuery = useQuery({
    queryKey: ['contacts', typeFilter],
    queryFn: () => fetchContacts(typeFilter === 'all' ? undefined : typeFilter),
  });

  const contacts = useMemo(() => contactsQuery.data || [], [contactsQuery.data]);

  const searchQuery = useQuery({
    queryKey: ['chat-search', selectedContact, keyword, kValue],
    queryFn: () => searchChat(selectedContact, keyword, kValue),
    enabled: !!selectedContact && keyword.trim().length > 0,
  });

  const summaryMutation = useMutation({
    mutationFn: (vars: { contact: string; limit: number }) => summarizeChat(vars.contact, vars.limit, 'Chinese'),
    onSuccess: (res) => {
      setSummaryText(res?.summary || '无内容');
      setSummaryOpen(true);
    },
    onError: () => toast.show('获取摘要失败', 'error'),
  });

  const notifyMutation = useMutation({
    mutationFn: (vars: { contact: string; limit: number }) => notifyChat(vars.contact, vars.limit),
    onSuccess: (res) => {
      setNotifyList(res?.data || []);
      setNotifyOpen(true);
    },
    onError: () => toast.show('获取重要消息失败', 'error'),
  });

  const replyQuery = useQuery({
    queryKey: ['reply-setting', selectedContact],
    queryFn: () => getReplySetting(selectedContact),
    enabled: !!selectedContact,
  });

  const updateReplyMutation = useMutation({
    mutationFn: (enabled: boolean) => updateReplySetting(selectedContact, enabled),
    onSuccess: () => {
      toast.show('已更新自动回复');
      queryClient.invalidateQueries({ queryKey: ['reply-setting', selectedContact] });
    },
    onError: () => toast.show('更新失败', 'error'),
  });

  const vectorDbQuery = useQuery({
    queryKey: ['vector-dbs'],
    queryFn: () => listVectorDBs(),
  });

  const switchVectorMutation = useMutation({
    mutationFn: (db: string) => switchVectorDB(db),
    onSuccess: () => {
      toast.show('已切换向量库', 'success');
      queryClient.invalidateQueries({ queryKey: ['vector-dbs'] });
    },
    onError: () => toast.show('切换失败', 'error'),
  });

  const sendMessageMutation = useMutation({
    mutationFn: () =>
      sendTestMessage({
        contact_id: selectedContact,
        message_type: messageType,
        raw_message: testMsg || '[空白消息]',
        is_at: messageType === 'group',
      }),
    onSuccess: (res) => {
      const reply = res?.reply || '';
      toast.show(reply ? `后端回复: ${reply}` : '消息已发送');
    },
    onError: () => toast.show('发送失败', 'error'),
  });

  return (
    <div>
      <div className="toolbar">
        <div>
          <div className="breadcrumbs">聊天 / RAG 搜索 / 自动回复</div>
          <h2 style={{ margin: '4px 0' }}>QQ 风格聊天助手</h2>
        </div>
      </div>
      <div className="split">
        <div className="panel">
          <div className="section-title">联系人</div>
          <div className="form-row" style={{ marginBottom: 8 }}>
            <select className="select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="all">全部</option>
              <option value="group">群聊</option>
              <option value="private">私聊</option>
            </select>
            <button className="button secondary" onClick={() => contactsQuery.refetch()} disabled={contactsQuery.isLoading}>
              刷新
            </button>
          </div>
          <div className="list">
            {contactsQuery.isLoading && <div className="muted">加载中...</div>}
            {!contactsQuery.isLoading && contacts.length === 0 && <div className="muted">暂无联系人</div>}
            {contacts.map((c) => {
              const cid = getContactId(c);
              const label = getContactLabel(c);
              return (
                <div
                  key={cid}
                  className={`list-item ${selectedContact === cid ? 'active' : ''}`}
                  onClick={() => setSelectedContact(cid)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>{label}</span>
                    {c.type && <span className="tag outline">{c.type}</span>}
                  </div>
                  {c.group_name && <div className="muted">群名: {c.group_name}</div>}
                </div>
              );
            })}
          </div>
        </div>

        <div className="panel">
          <div className="section-title">聊天检索</div>
          <div className="form-row" style={{ marginBottom: 10 }}>
            <input
              className="input"
              placeholder="输入关键词以检索聊天向量库"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              style={{ flex: 1 }}
            />
            <input
              className="input"
              type="number"
              min={1}
              max={50}
              value={kValue}
              onChange={(e) => setKValue(Number(e.target.value))}
              style={{ width: 80 }}
            />
            <button
              className="button"
              onClick={() => searchQuery.refetch()}
              disabled={!selectedContact || !keyword.trim()}
            >
              搜索
            </button>
          </div>
          {searchQuery.isLoading && <div className="muted">检索中...</div>}
          {!searchQuery.isLoading && (!searchQuery.data || searchQuery.data.length === 0) && (
            <div className="muted">暂无结果，输入关键词后搜索。</div>
          )}
          <div className="chat-bubbles">
            {searchQuery.data?.map((item: any, idx: number) => {
              const meta = item.metadata || {};
              const sender = meta.name || meta.sender || '对话';
              const time = meta.time || '';
              const content = item.content || item.page_content || '';
              return (
                <div key={idx} className="bubble other">
                  <div className="meta">
                    {sender} {time && `· ${time}`}
                  </div>
                  <div>{content}</div>
                  {item.next_messages && item.next_messages.length > 0 && (
                    <div className="muted" style={{ marginTop: 6 }}>
                      后续 {item.next_messages.length} 条：
                      {item.next_messages.slice(0, 3).map((n: any, i: number) => (
                        <div key={i}>- {n.content}</div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="panel">
          <div className="section-title">快捷操作</div>
          <div className="pill-row" style={{ marginBottom: 8 }}>
            <button
              className="button secondary"
              onClick={() => summaryMutation.mutate({ contact: selectedContact, limit: 100 })}
              disabled={!selectedContact || summaryMutation.isPending}
            >
              聊天摘要
            </button>
            <button
              className="button secondary"
              onClick={() => notifyMutation.mutate({ contact: selectedContact, limit: 80 })}
              disabled={!selectedContact || notifyMutation.isPending}
            >
              重要提醒
            </button>
          </div>

          <div className="section-title">自动回复</div>
          {replyQuery.isLoading && <div className="muted">读取中...</div>}
          {selectedContact && !replyQuery.isLoading && (
            <div className="form-row">
              <span className="tag outline">状态</span>
              <span className="muted">
                {replyQuery.data?.enabled ?? replyQuery.data?.success ? '已开启' : '已关闭'}
              </span>
              <button
                className="button"
                onClick={() => updateReplyMutation.mutate(!(replyQuery.data?.enabled ?? false))}
                disabled={updateReplyMutation.isPending}
              >
                {replyQuery.data?.enabled ? '关闭' : '开启'}
              </button>
            </div>
          )}
          {!selectedContact && <div className="muted">选择联系人以管理自动回复</div>}

          <div className="section-title">向量库</div>
          {vectorDbQuery.isLoading && <div className="muted">加载中...</div>}
          {vectorDbQuery.data && (
            <div className="form-row">
              <div className="muted" style={{ flex: 1 }}>
                当前：{vectorDbQuery.data.current_db || '未加载'}
              </div>
              <select
                className="select"
                style={{ flex: 1 }}
                onChange={(e) => switchVectorMutation.mutate(e.target.value)}
                defaultValue=""
              >
                <option value="" disabled>
                  切换向量库
                </option>
                {vectorDbQuery.data.databases?.map((db) => (
                  <option key={db} value={db}>
                    {db}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="section-title">发送测试消息</div>
          <div className="form-row">
            <select className="select" value={messageType} onChange={(e) => setMessageType(e.target.value as any)}>
              <option value="group">群聊</option>
              <option value="private">私聊</option>
            </select>
            <input
              className="input"
              placeholder="输入测试文本，后端将记录并自动回复"
              value={testMsg}
              onChange={(e) => setTestMsg(e.target.value)}
              style={{ flex: 1 }}
            />
          </div>
          <button
            className="button"
            style={{ marginTop: 8, width: '100%' }}
            onClick={() => sendMessageMutation.mutate()}
            disabled={!selectedContact}
          >
            发送到后端
          </button>
          <div className="muted" style={{ marginTop: 4 }}>
            使用当前选择的联系人 ID 作为群号/QQ 号，便于本地联调。
          </div>
        </div>
      </div>

      <Modal open={summaryOpen} onClose={() => setSummaryOpen(false)} title="聊天摘要">
        <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{summaryText || '暂无内容'}</p>
      </Modal>

      <Modal open={notifyOpen} onClose={() => setNotifyOpen(false)} title="重要消息">
        {notifyList.length === 0 && <div className="muted">无重要消息</div>}
        <div className="list">
          {notifyList.map((n, idx) => (
            <div key={idx} className="list-item">
              <div className="muted">{n.time}</div>
              <div style={{ fontWeight: 700 }}>{n.sender}</div>
              <div>{n.content}</div>
              {n.reason && <div className="muted">原因：{n.reason}</div>}
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
};

export default ChatPage;
