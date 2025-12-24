import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchContacts, fetchImages, translateImage } from '../api/endpoints';
import type { Contact } from '../api/types';
import { downloadBlob } from '../api/client';
import { useToast } from '../components/ToastProvider';

const getContactId = (c: Contact): string =>
  c.id || (c as any).contact_id || (c as any).group_id || (c as any).user_id || c.name || c.nickname || '';

const ImagesPage = () => {
  const toast = useToast();
  const [contactId, setContactId] = useState('');
  const [targetLang, setTargetLang] = useState('Chinese');

  const contactsQuery = useQuery({
    queryKey: ['contacts'],
    queryFn: () => fetchContacts(),
  });

  useEffect(() => {
    if (contactsQuery.data && contactsQuery.data.length > 0 && !contactId) {
      setContactId(getContactId(contactsQuery.data[0]));
    }
  }, [contactsQuery.data, contactId]);

  const imagesQuery = useQuery({
    queryKey: ['images', contactId],
    queryFn: () => fetchImages(contactId),
    enabled: !!contactId,
  });

  const translateMutation = useMutation({
    mutationFn: (filePath: string) => translateImage(filePath, targetLang),
    onSuccess: (res, filePath) => {
      const filename = filePath.split(/[\\/]/).pop() || 'translated.jpg';
      downloadBlob(res.data, filename.replace(/\.[^.]+$/, '_translated.jpg'));
      toast.show('图片翻译完成，开始下载', 'success');
    },
    onError: () => toast.show('翻译失败', 'error'),
  });

  const contacts = useMemo(() => contactsQuery.data || [], [contactsQuery.data]);

  return (
    <div>
      <div className="toolbar">
        <div>
          <div className="breadcrumbs">图片 / 翻译</div>
          <h2 style={{ margin: '4px 0' }}>图片翻译</h2>
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
        </div>
      </div>

      {imagesQuery.isLoading && <div className="muted">加载图片列表...</div>}
      {!imagesQuery.isLoading && (!imagesQuery.data || imagesQuery.data.length === 0) && (
        <div className="muted">暂无图片</div>
      )}

      <div className="grid-gallery">
        {imagesQuery.data?.map((img) => (
          <div className="thumb" key={img.path || img.name}>
            <div className="tag outline">本地路径</div>
            <div className="path">{img.path}</div>
            {img.time && <div className="muted">{img.time}</div>}
            <button className="button" onClick={() => translateMutation.mutate(img.path)} disabled={translateMutation.isPending}>
              翻译并下载
            </button>
          </div>
        ))}
      </div>
      <div className="muted" style={{ marginTop: 8 }}>
        缩略图需要静态文件服务；当前展示路径以便确认后端可访问。
      </div>
    </div>
  );
};

export default ImagesPage;
