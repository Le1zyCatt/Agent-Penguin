import { useMemo, useState, useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  fetchContacts,
  searchChat,
  getChatHistory,
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
import MarkdownRenderer from '../components/MarkdownRenderer';

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

  // For local search functionality
  const [localSearchResults, setLocalSearchResults] = useState<ChatHistoryItem[]>([]);
  const [isLocalSearching, setIsLocalSearching] = useState(false);

  // Ref for chat bubbles container to auto-scroll
  const chatBubblesRef = useRef<HTMLDivElement>(null);

  const toast = useToast();
  const queryClient = useQueryClient();

  const contactsQuery = useQuery({
    queryKey: ['contacts', typeFilter],
    queryFn: () => fetchContacts(typeFilter === 'all' ? undefined : typeFilter),
  });

  // New query to fetch full chat history for local search
  const historyQuery = useQuery<ChatHistoryItem[]>({
    queryKey: ['chat-history', selectedContact],
    queryFn: () => getChatHistory(selectedContact),
    enabled: !!selectedContact,
  });

  const contacts = useMemo(() => contactsQuery.data || [], [contactsQuery.data]);

  // Local search functionality with debouncing for better performance
  useEffect(() => {
    if (keyword.trim() && historyQuery.data) {
      setIsLocalSearching(true);

      // Add a small delay to avoid excessive filtering while typing
      const timer = setTimeout(() => {
        // Perform local search in the fetched history
        const results = historyQuery.data.filter(item => {
          const searchText = `${item.text || ''} ${item.extracted_content || ''}`.toLowerCase();
          return searchText.includes(keyword.toLowerCase().trim());
        }).slice(0, kValue);

        setLocalSearchResults(results);
        setIsLocalSearching(false);
      }, 300); // 300ms delay

      return () => clearTimeout(timer);
    } else {
      setLocalSearchResults([]);
      setIsLocalSearching(false);
    }
  }, [keyword, historyQuery.data, kValue]);

  // Auto-scroll to bottom when chat history changes (but not during search)
  useEffect(() => {
    // Only auto-scroll when showing full history, not during search
    if (chatBubblesRef.current && !keyword.trim()) {
      chatBubblesRef.current.scrollTop = chatBubblesRef.current.scrollHeight;
    }
  }, [historyQuery.data, keyword]);

  // Auto-scroll to top when search results change
  useEffect(() => {
    if (chatBubblesRef.current && keyword.trim()) {
      chatBubblesRef.current.scrollTop = 0; // Scroll to top for search results
    }
  }, [localSearchResults, keyword]);

  // Original search functionality (for comparison)
  const searchQuery = useQuery({
    queryKey: ['chat-search', selectedContact, keyword, kValue],
    queryFn: () => searchChat(selectedContact, keyword, kValue),
    enabled: false, // Disable this since we're using local search
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
          <div className="section-title">聊天记录</div>
          <div className="form-row" style={{ marginBottom: 10 }}>
            <input
              className="input"
              placeholder="输入关键词搜索聊天记录"
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
          </div>

          {historyQuery.isLoading && <div className="muted">加载聊天记录中...</div>}

          {!historyQuery.isLoading && historyQuery.data && (
            <div className="muted" style={{ marginBottom: 10 }}>
              共 {historyQuery.data.length} 条记录
            </div>
          )}

          {/* Show all chat history if no search term, otherwise show filtered results */}
          <div className="chat-bubbles" ref={chatBubblesRef}>
            {(() => {
              const messagesToDisplay = keyword.trim()
                ? localSearchResults
                : (historyQuery.data || []).slice(-(kValue || 50)); // Show last N messages by default

              return messagesToDisplay.map((item: ChatHistoryItem, idx: number) => {
                const sender = item.name || '未知';
                const time = item.time || '';
                // Combine text and extracted content for display
                const content = (item.text || '') + (item.extracted_content ? ` ${item.extracted_content}` : '');

                // Function to highlight keywords safely
                const highlightText = (text: string) => {
                  if (!keyword.trim()) return [<span key={0}>{text}</span>];

                  const regex = new RegExp(`(${keyword})`, 'gi');
                  const parts = text.split(regex);

                  return parts.map((part, i) => {
                    const isMatch = regex.test(part);
                    return isMatch ? (
                      <mark key={i} style={{ backgroundColor: '#fff9b1', padding: '0 2px' }}>
                        {part}
                      </mark>
                    ) : (
                      <span key={i}>{part}</span>
                    );
                  });
                };

                return (
                  <div key={idx} className="bubble other">
                    <div className="meta">
                      {sender} {time && `· ${time}`}
                    </div>
                    {item.content_type === 'image' && item.local_path ? (
                      // Render image if content_type is image
                      <div className="image-container" style={{ margin: '8px 0' }}>
                        <img
                          src={`/api/file?path=${encodeURIComponent(item.local_path)}`}
                          alt={item.local_path.split('/').pop() || 'Chat image'}
                          style={{
                            maxWidth: '200px',
                            maxHeight: '200px',
                            borderRadius: '8px',
                            border: '1px solid #ddd',
                            objectFit: 'contain',
                            cursor: 'pointer',
                            transition: 'transform 0.2s, box-shadow 0.2s'
                          }}
                          onClick={() => {
                            // Open image in new tab when clicked
                            window.open(`/api/file?path=${encodeURIComponent(item.local_path)}`, '_blank');
                          }}
                          onLoad={(e) => {
                            console.log(`Image loaded successfully: ${item.local_path}`);
                          }}
                          onError={(e) => {
                            console.error(`Failed to load image: ${item.local_path}`, e);
                            const target = e.target as HTMLImageElement;
                            // Create a simple placeholder image
                            target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDIwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiBmaWxsPSIjRjBGMEYwIi8+Cjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIiBmaWxsPSIjODg4Ij5JbWFnZTwvdGV4dD4KPC9zdmc+';
                          }}
                        />
                      </div>
                    ) : (
                      <div>{highlightText(content)}</div>
                    )}
                    {item.content_type && item.content_type !== 'text' && (
                      <div className="muted" style={{ marginTop: 6 }}>
                        [{item.content_type}] {item.local_path && `路径: ${item.local_path}`}
                      </div>
                    )}
                  </div>
                );
              });
            })()}
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
              <div className="muted" style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                当前：{vectorDbQuery.data.current_db?.split('/').pop() || '未加载'}
              </div>
              <select
                className="select"
                style={{ flex: 1, minWidth: 0 }}
                onChange={(e) => switchVectorMutation.mutate(e.target.value)}
                defaultValue=""
              >
                <option value="" disabled>
                  切换向量库
                </option>
                {vectorDbQuery.data.databases?.map((db) => (
                  <option key={db} value={db}>
                    {db.split('/').pop() || db} {/* 显示路径的最后一部分 */}
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
        {summaryText ? <MarkdownRenderer content={summaryText} /> : <p>暂无内容</p>}
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
