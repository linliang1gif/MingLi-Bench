import React, { useEffect, useState } from 'react';
import { Empty, Spin, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import api from '../services/api';

import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

dayjs.extend(utc);
const fmtLocal = (ts) => ts ? dayjs.utc(ts).local().format('YYYY-MM-DD HH:mm') : '';

export default function History() {
  const nav = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.history()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageBanner
        title="历史记录"
        subtitle="对话与报告的统一时间线"
        quote="过往可寻，方知来路。"
      />
      <PaperCard title="时间线">
        {loading ? <Spin /> :
          items.length === 0 ? <Empty description="暂无记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {items.map((it) => (
                <div
                  key={`${it.kind}-${it.id}`}
                  onClick={() => nav(it.kind === 'report' ? `/reports/${it.id}` : `/`)}
                  style={{
                    cursor: 'pointer',
                    padding: '12px 14px',
                    border: '1px solid var(--ml-divider)',
                    borderRadius: 12,
                    background: 'rgba(94, 139, 126, 0.06)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Tag style={{
                      borderColor: 'var(--ml-bronze)',
                      color: 'var(--ml-bronze)',
                      background: 'transparent',
                    }}>{it.kind === 'report' ? '报告' : '对话'}</Tag>
                    <span style={{ fontFamily: 'var(--ml-font-serif)', color: 'var(--ml-text)' }}>{it.title}</span>
                  </div>
                  <span style={{ color: 'var(--ml-text-faint)', fontSize: 12 }}>
                    {fmtLocal(it.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          )}
      </PaperCard>
    </div>
  );
}
