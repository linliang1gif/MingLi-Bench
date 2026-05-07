import React, { useEffect, useState } from 'react';
import { Select, Spin, Empty, Button, Space, Alert } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../services/api';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

export default function ChartAnalysis() {
  const { subjectId: subjectIdInUrl } = useParams();
  const nav = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [activeId, setActiveId] = useState(subjectIdInUrl ? Number(subjectIdInUrl) : null);
  const [chart, setChart] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.listSubjects().then((rows) => {
      setSubjects(rows);
      if (!activeId && rows[0]) setActiveId(rows[0].id);
    });
  }, []);

  useEffect(() => {
    if (!activeId) return;
    setLoading(true);
    api.getChart(activeId).then(setChart).catch(() => setChart(null)).finally(() => setLoading(false));
  }, [activeId]);

  const subj = subjects.find((s) => s.id === activeId);

  return (
    <div>
      <PageBanner
        title="命盘分析"
        subtitle="基于命主出生信息推算的简化四柱与五行"
        quote="盘为据，理为衡。"
        extra={
          <Space>
            <Select
              style={{ width: 220 }}
              placeholder="选择命主"
              value={activeId}
              onChange={(v) => { setActiveId(v); nav(`/chart/${v}`); }}
              options={subjects.map((s) => ({ value: s.id, label: `${s.nickname} · ${s.birth_date || '—'}` }))}
            />
            <Button
              icon={<ReloadOutlined />}
              disabled={!activeId}
              onClick={async () => {
                setLoading(true);
                try { setChart(await api.generateChart(activeId)); } finally { setLoading(false); }
              }}
            >
              重新推算
            </Button>
          </Space>
        }
      />

      {!activeId ? (
        <PaperCard title="尚未选择命主"><Empty description="请先选择或创建命主" /></PaperCard>
      ) : loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spin /></div>
      ) : !chart || chart.available === false ? (
        <Alert
          type="warning"
          message="无法生成命盘"
          description={chart?.reason || '出生日期缺失或格式错误，请在命主档案中补全后再试'}
          showIcon
        />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <PaperCard title="四柱" extra={subj ? `${subj.nickname} · ${subj.gender || '—'} · ${subj.birth_date}` : ''}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
              {['year', 'month', 'day', 'hour'].map((k) => {
                const c = (chart.pillars || {})[k] || {};
                return (
                  <div
                    key={k}
                    style={{
                      border: '1px solid var(--ml-divider)',
                      background: 'rgba(94, 139, 126, 0.06)',
                      borderRadius: 12,
                      padding: '20px 8px',
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ color: 'var(--ml-text-faint)', fontSize: 12 }}>{c.label || k}</div>
                    <div style={{ fontFamily: 'var(--ml-font-serif)', fontSize: 36, color: 'var(--ml-text)', marginTop: 8 }}>
                      {c.stem || '—'}{c.branch || ''}
                    </div>
                  </div>
                );
              })}
            </div>
          </PaperCard>

          <PaperCard title="五行分布">
            {chart.wuxing?.counts ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
                {Object.entries(chart.wuxing.counts).map(([w, c]) => (
                  <div key={w} style={{ textAlign: 'center', padding: 10, border: '1px solid var(--ml-divider)', borderRadius: 10 }}>
                    <div style={{ fontFamily: 'var(--ml-font-serif)', color: 'var(--ml-text)' }}>{w}</div>
                    <div style={{ color: 'var(--ml-bronze)', fontSize: 24, marginTop: 4 }}>{c}</div>
                  </div>
                ))}
              </div>
            ) : <Empty description="暂无五行数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </PaperCard>

          {chart.summary && (
            <PaperCard title="命盘简析">
              <div style={{ color: 'var(--ml-text)', lineHeight: 1.85 }}>{chart.summary}</div>
            </PaperCard>
          )}
        </Space>
      )}
    </div>
  );
}
