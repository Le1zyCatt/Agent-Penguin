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
          <div className="thumb" key={img.file_path || img.file_name}>
            <div className="image-preview-container">
              <img
                src={`/api/file?path=${encodeURIComponent(img.file_path)}`}
                alt={img.file_name}
                className="image-preview"
                onLoad={(e) => {
                  console.log(`Image loaded successfully: ${img.file_path}`);
                }}
                onClick={() => {
                  // Open image in new tab when clicked
                  window.open(`/api/file?path=${encodeURIComponent(img.file_path)}`, '_blank');
                }}
                onError={(e) => {
                  console.error(`Failed to load image: ${img.file_path}`, e);
                  const target = e.target as HTMLImageElement;
                  // 创建一个简单的占位图片（base64编码的SVG）
                  target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTUwIiBoZWlnaHQ9IjE1MCIgdmlld0JveD0iMCAwIDE1MCAxNTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxNTAiIGhlaWdodD0iMTUwIiBmaWxsPSIjRjBGMEYwIi8+Cjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iOSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iIGZpbGw9IiM4ODgiPkltYWdlPC90ZXh0Pgo8L3N2Zz4K';
                }}
                style={{
                  maxWidth: '100%',
                  maxHeight: '150px',
                  objectFit: 'contain',
                  cursor: 'pointer',
                  borderRadius: '8px',
                  border: '1px solid #eee'
                }}
              />
            </div>
            <div className="image-info">
              <div className="muted" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {img.file_name}
              </div>
              {img.time && <div className="muted">{img.time}</div>}
            </div>
            <button className="button" onClick={() => translateMutation.mutate(img.file_path)} disabled={translateMutation.isPending}>
              翻译并下载
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ImagesPage;
