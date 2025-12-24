import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchContacts, fetchDocs, summarizeDocs, translateDoc } from '../api/endpoints';
import type { Contact } from '../api/types';
import { downloadBlob } from '../api/client';
import Modal from '../components/Modal';
import { useToast } from '../components/ToastProvider';
import MarkdownRenderer from '../components/MarkdownRenderer';

const getContactId = (c: Contact): string =>
  c.id || (c as any).contact_id || (c as any).group_id || (c as any).user_id || c.name || c.nickname || '';

const FilesPage = () => {
  const toast = useToast();
  const [contactId, setContactId] = useState('');
  const [targetLang, setTargetLang] = useState('Chinese');
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryText, setSummaryText] = useState('');
  const [limit, setLimit] = useState(5);

  const contactsQuery = useQuery({
    queryKey: ['contacts'],
    queryFn: () => fetchContacts(),
  });

  useEffect(() => {
    if (contactsQuery.data && contactsQuery.data.length > 0 && !contactId) {
      setContactId(getContactId(contactsQuery.data[0]));
    }
  }, [contactsQuery.data, contactId]);

  const docsQuery = useQuery({
    queryKey: ['docs', contactId],
    queryFn: () => fetchDocs(contactId),
    enabled: !!contactId,
  });

  const summarizeMutation = useMutation({
    mutationFn: () => summarizeDocs(contactId, limit, targetLang),
    onSuccess: (res) => {
      setSummaryText(res?.summary || '无内容');
      setSummaryOpen(true);
    },
    onError: () => toast.show('生成摘要失败', 'error'),
  });

  const translateMutation = useMutation({
    mutationFn: (filePath: string) => translateDoc(filePath, targetLang),
    onSuccess: (res, filePath) => {
      const filename = filePath.split(/[\\/]/).pop() || 'translated.docx';
      downloadBlob(res.data, filename.replace(/\.[^.]+$/, '_translated.docx'));
      toast.show('翻译完成，开始下载', 'success');
    },
    onError: () => toast.show('翻译失败', 'error'),
  });

  const contacts = useMemo(() => contactsQuery.data || [], [contactsQuery.data]);

  return (
    <div>
      <div className="toolbar">
        <div>
          <div className="breadcrumbs">文件 / 翻译 / 摘要</div>
          <h2 style={{ margin: '4px 0' }}>文件处理</h2>
        </div>
        <div className="form-row">
          <select className="select" value={contactId} onChange={(e) => setContactId(e.target.value)}>
            {contacts.map((c) => (
              <option key={getContactId(c)} value={getContactId(c)}>
                {c.name || c.nickname || c.group_name || getContactId(c)}
              </option>
            ))}
          </select>
          <select className="select" value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
            <option value="Chinese">Chinese</option>
            <option value="English">English</option>
            <option value="Japanese">Japanese</option>
          </select>
          <button className="button secondary" onClick={() => summarizeMutation.mutate()} disabled={!contactId}>
            最近文件总结
          </button>
        </div>
      </div>

      {docsQuery.isLoading && <div className="muted">加载文件列表...</div>}
      {!docsQuery.isLoading && (!docsQuery.data || docsQuery.data.length === 0) && (
        <div className="muted">暂无文件</div>
      )}

      <div className="cards-grid">
        {docsQuery.data?.map((doc) => (
          <div className="card" key={doc.file_path || doc.file_name}>
            <h3>{doc.file_name}</h3>
            <p className="muted" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {doc.file_path}
            </p>
            {doc.time && <p className="muted">时间：{doc.time}</p>}
            {doc.extracted_content && (
              <p className="muted" style={{ maxHeight: 80, overflow: 'auto' }}>
                预览：{doc.extracted_content.slice(0, 160)}
              </p>
            )}
            <div className="pill-row" style={{ marginTop: 8 }}>
              <button
                className="button"
                onClick={() => translateMutation.mutate(doc.file_path)}
                disabled={translateMutation.isPending}
              >
                翻译并下载
              </button>
            </div>
          </div>
        ))}
      </div>

      <Modal open={summaryOpen} onClose={() => setSummaryOpen(false)} title="最近文件总结">
        <div className="form-row" style={{ marginBottom: 10 }}>
          <label className="muted">数量</label>
          <input
            className="input"
            type="number"
            min={1}
            max={20}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            style={{ width: 80 }}
          />
        </div>
        {summaryText ? <MarkdownRenderer content={summaryText} /> : <p>暂无内容</p>}
      </Modal>
    </div>
  );
};

export default FilesPage;
