import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { notifyChat, summarizeChat } from '../api/endpoints';
import Modal from '../components/Modal';
import { useToast } from '../components/ToastProvider';

const SummaryPage = () => {
  const toast = useToast();
  const [contactId, setContactId] = useState('');
  const [limit, setLimit] = useState(80);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryText, setSummaryText] = useState('');
  const [notifyOpen, setNotifyOpen] = useState(false);
  const [notifyList, setNotifyList] = useState<any[]>([]);
  const [targetLang, setTargetLang] = useState('Chinese');

  const summaryMutation = useMutation({
    mutationFn: () => summarizeChat(contactId, limit, targetLang),
    onSuccess: (res) => {
      setSummaryText(res?.summary || '无内容');
      setSummaryOpen(true);
    },
    onError: () => toast.show('获取摘要失败', 'error'),
  });

  const notifyMutation = useMutation({
    mutationFn: () => notifyChat(contactId, limit),
    onSuccess: (res) => {
      setNotifyList(res?.data || []);
      setNotifyOpen(true);
    },
    onError: () => toast.show('获取提醒失败', 'error'),
  });

  return (
    <div>
      <div className="toolbar">
        <div>
          <div className="breadcrumbs">摘要 / 提醒</div>
          <h2 style={{ margin: '4px 0' }}>聊天摘要与提醒</h2>
        </div>
        <div className="form-row">
          <input
            className="input"
            placeholder="输入 contact_id (群号或 QQ)"
            value={contactId}
            onChange={(e) => setContactId(e.target.value)}
            style={{ minWidth: 220 }}
          />
          <input
            className="input"
            type="number"
            min={10}
            max={500}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            style={{ width: 100 }}
          />
          <select className="select" value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
            <option value="Chinese">Chinese</option>
            <option value="English">English</option>
            <option value="Japanese">Japanese</option>
          </select>
          <button className="button" onClick={() => summaryMutation.mutate()} disabled={!contactId}>
            聊天摘要
          </button>
          <button className="button secondary" onClick={() => notifyMutation.mutate()} disabled={!contactId}>
            重要消息
          </button>
        </div>
      </div>

      <div className="card">
        <h3>说明</h3>
        <p className="muted">
          直接调用后端 /api/msg/summarize 与 /api/msg/notification。
          确保 contact_id 在后端历史记录中已存在，否则会返回“未找到”。
        </p>
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

export default SummaryPage;
