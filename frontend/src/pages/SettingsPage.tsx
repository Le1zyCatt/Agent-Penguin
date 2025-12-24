import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getReplySetting, listReplySettings, updateReplySetting, listVectorDBs, switchVectorDB } from '../api/endpoints';
import { useToast } from '../components/ToastProvider';
import type { VectorDBList, ReplySettingResponse } from '../api/types';

const SettingsPage = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [contactId, setContactId] = useState('');
  const [enabled, setEnabled] = useState(false);
  const [selectedDb, setSelectedDb] = useState('');

  const replyListQuery = useQuery<ReplySettingResponse>({
    queryKey: ['reply-settings-all'],
    queryFn: () => listReplySettings(),
  });

  const currentSettingQuery = useQuery<ReplySettingResponse | null>({
    queryKey: ['reply-setting', contactId],
    queryFn: () => (contactId ? getReplySetting(contactId) : Promise.resolve(null)),
    enabled: !!contactId,
  });

  useEffect(() => {
    const res = currentSettingQuery.data;
    if (res && typeof res.enabled === 'boolean') {
      setEnabled(res.enabled);
    }
  }, [currentSettingQuery.data]);

  const updateReplyMutation = useMutation({
    mutationFn: () => updateReplySetting(contactId, enabled),
    onSuccess: () => {
      toast.show('自动回复已更新', 'success');
      queryClient.invalidateQueries({ queryKey: ['reply-settings-all'] });
      queryClient.invalidateQueries({ queryKey: ['reply-setting', contactId] });
    },
    onError: () => toast.show('更新失败', 'error'),
  });

  const vectorDbQuery = useQuery<VectorDBList>({
    queryKey: ['vector-dbs'],
    queryFn: () => listVectorDBs(),
  });

  useEffect(() => {
    const res = vectorDbQuery.data;
    if (res?.databases && res.databases.length > 0 && !selectedDb) {
      setSelectedDb(res.current_db || res.databases[0]);
    }
  }, [vectorDbQuery.data, selectedDb]);

  const switchVectorMutation = useMutation({
    mutationFn: (db: string) => switchVectorDB(db),
    onSuccess: () => {
      toast.show('已切换向量库', 'success');
      queryClient.invalidateQueries({ queryKey: ['vector-dbs'] });
    },
    onError: () => toast.show('切换失败', 'error'),
  });

  return (
    <div>
      <div className="toolbar">
        <div>
          <div className="breadcrumbs">设置</div>
          <h2 style={{ margin: '4px 0' }}>系统设置</h2>
        </div>
      </div>

      <div className="cards-grid">
        <div className="card">
          <h3>自动回复设置</h3>
          <p className="muted">读取并更新指定 contact_id 的自动回复开关。</p>
          <div className="form-row" style={{ marginBottom: 8 }}>
            <input
              className="input"
              placeholder="contact_id (群号/QQ)"
              value={contactId}
              onChange={(e) => setContactId(e.target.value)}
            />
            <select className="select" value={enabled ? 'on' : 'off'} onChange={(e) => setEnabled(e.target.value === 'on')}>
              <option value="on">开启</option>
              <option value="off">关闭</option>
            </select>
            <button className="button" onClick={() => updateReplyMutation.mutate()} disabled={!contactId}>
              保存
            </button>
          </div>
          {currentSettingQuery.isLoading && <div className="muted">读取中...</div>}
          {contactId && currentSettingQuery.data && (
            <div className="muted">当前状态：{currentSettingQuery.data?.enabled ? '已开启' : '已关闭'}</div>
          )}
        </div>

        <div className="card">
          <h3>向量库管理</h3>
          <p className="muted">查看当前向量库并在已存在的库之间切换。</p>
          {vectorDbQuery.isLoading && <div className="muted">加载中...</div>}
          {vectorDbQuery.data && (
            <>
              <div className="muted" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                当前：{vectorDbQuery.data?.current_db || '未加载'}
              </div>
              <div className="form-row" style={{ marginTop: 8 }}>
                <select
                  className="select"
                  value={selectedDb}
                  onChange={(e) => setSelectedDb(e.target.value)}
                  style={{ flex: 1, minWidth: 0 }}
                >
                  <option value="" disabled>选择向量库</option>
                  {vectorDbQuery.data?.databases?.map((db: string) => (
                    <option key={db} value={db}>
                      {db.split('/').pop() || db} {/* 显示路径的最后一部分 */}
                    </option>
                  ))}
                </select>
                <button className="button" onClick={() => selectedDb && switchVectorMutation.mutate(selectedDb)}>
                  切换
                </button>
              </div>
            </>
          )}
        </div>

        <div className="card">
          <h3>已配置的自动回复</h3>
          {replyListQuery.isLoading && <div className="muted">加载中...</div>}
          {!replyListQuery.isLoading && (
            <div className="list" style={{ maxHeight: 240 }}>
              {replyListQuery.data?.settings &&
                Object.entries(replyListQuery.data.settings).map(([id, en]) => (
                  <div className="list-item" key={id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>{id}</span>
                      <span className="tag outline">{en ? '开启' : '关闭'}</span>
                    </div>
                  </div>
                ))}
              {(!replyListQuery.data || !replyListQuery.data.settings) && <div className="muted">暂无配置</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
