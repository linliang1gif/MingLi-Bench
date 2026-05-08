import React, { useEffect, useState } from 'react';
import { List, Empty, Spin, Button, Space, Select, Modal } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import api from '../services/api';

import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';
import MarkdownView from '../components/MarkdownView';

dayjs.extend(utc);
const fmtLocal = (ts) => ts ? dayjs.utc(ts).local().format('YYYY-MM-DD HH:mm') : '';

const TYPES = [
  { value: 'general', label: '综合' },
  { value: 'wealth', label: '财运' },
  { value: 'career', label: '事业' },
  { value: 'relationship', label: '感情' },
  { value: 'yearly', label: '流年' },
];

export default function Reports() {
  const nav = useNavigate();
  const { id: paramId } = useParams();

  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState(undefined);
  const [reportType, setReportType] = useState('general');
  const [genBusy, setGenBusy] = useState(false);

  function refresh() {
    setLoading(true);
    api.listReports().then(setReports).finally(() => setLoading(false));
  }
  useEffect(() => {
    refresh();
    api.listSubjects().then(setSubjects);
  }, []);

  // 直链 /reports/:id 时打开 Modal
  const [activeId, setActiveId] = useState(paramId ? Number(paramId) : null);
  const [active, setActive] = useState(null);
  useEffect(() => {
    if (!activeId) { setActive(null); return; }
    api.getReport(activeId).then(setActive).catch(() => setActive(null));
  }, [activeId]);

  async function onGenerate() {
    if (!subjectId) return;
    setGenBusy(true);
    try {
      const r = await api.generateReport({ subjectId, reportType });
      refresh();
      setActiveId(r.id);
    } finally { setGenBusy(false); }
  }

  return (
    <div>
      <PageBanner
        title="分析报告"
        subtitle="按命主与类别一键生成的结构化分析"
        quote="文以载道，书以载证。"
        extra={
          <Space>
            <Select
              placeholder="选择命主"
              style={{ width: 200 }}
              value={subjectId}
              onChange={setSubjectId}
              options={subjects.map((s) => ({ value: s.id, label: s.nickname }))}
            />
            <Select value={reportType} onChange={setReportType} style={{ width: 130 }} options={TYPES} />
            <Button type="primary" disabled={!subjectId} loading={genBusy} onClick={onGenerate}>生成报告</Button>
          </Space>
        }
      />

      <PaperCard title="报告列表" extra={`共 ${reports.length} 篇`}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 30 }}><Spin /></div>
        ) : reports.length === 0 ? (
          <Empty description="尚无报告，先生成一份吧" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            className="ml-list"
            dataSource={reports}
            renderItem={(r) => (
              <List.Item
                style={{ cursor: 'pointer' }}
                onClick={() => { setActiveId(r.id); nav(`/reports/${r.id}`); }}
              >
                <List.Item.Meta
                  title={
                    <span style={{ fontFamily: 'var(--ml-font-serif)', color: 'var(--ml-text)' }}>{r.title}</span>
                  }
                  description={
                    <span style={{ color: 'var(--ml-text-faint)', fontSize: 12 }}>
                      {fmtLocal(r.created_at)} · {TYPES.find((t)=>t.value===r.report_type)?.label || r.report_type}
                    </span>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </PaperCard>

      <Modal
        title={active?.title || '报告详情'}
        open={!!activeId}
        width={820}
        onCancel={() => { setActiveId(null); nav('/reports'); }}
        footer={null}
        styles={{ body: { maxHeight: '70vh', overflow: 'auto', padding: '20px 24px' } }}
      >
        {active ? <MarkdownView content={active.content} /> : <Spin />}
      </Modal>
    </div>
  );
}
