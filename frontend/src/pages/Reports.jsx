import React, { useEffect, useState } from 'react';
import { Empty, Input, List, Segmented, Select, Space, Spin, Button, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import api from '../services/api';

import AnalysisModeSelector, { AnalysisModeTag } from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

dayjs.extend(utc);
const fmtLocal = (ts) => ts ? dayjs.utc(ts).local().format('YYYY-MM-DD HH:mm') : '';

const GENERATE_TYPES = [
  { value: 'general', label: '综合命理分析' },
  { value: 'wealth', label: '财运专项分析' },
  { value: 'career', label: '事业专项分析' },
  { value: 'relationship', label: '感情专项分析' },
  { value: 'yearly', label: '流年走势分析' },
];

const TYPES = [
  ...GENERATE_TYPES,
  { value: 'fengshui_basic', label: '阳宅基础报告' },
  { value: 'fengshui_xuankong_report', label: '玄空飞星报告' },
  { value: 'fengshui_photo_report', label: '拍照风水报告' },
  { value: 'landscape_photo_report', label: '外局拍照研究报告' },
  { value: 'heritage_risk_record_report', label: '文保风险记录报告' },
  { value: 'yinzhai_study_report', label: '阴宅研究报告' },
  { value: 'tianxing_fengshui_report', label: '天星风水报告' },
];

const typeLabel = (value) => TYPES.find((t) => t.value === value)?.label || value || '未知类型';

export default function Reports() {
  const nav = useNavigate();

  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState(undefined);
  const [reportType, setReportType] = useState('general');
  const [analysisMode, setAnalysisMode] = useState('safe');
  const [genBusy, setGenBusy] = useState(false);
  const [filterType, setFilterType] = useState('');
  const [modeFilter, setModeFilter] = useState('all');
  const [referenceFilter, setReferenceFilter] = useState('all');
  const [keyword, setKeyword] = useState('');
  const [sortOrder, setSortOrder] = useState('desc');

  function refresh() {
    setLoading(true);
    api.listReports().then(setReports).finally(() => setLoading(false));
  }
  useEffect(() => {
    refresh();
    api.listSubjects().then(setSubjects);
  }, []);

  async function onGenerate() {
    if (!subjectId) return;
    setGenBusy(true);
    try {
      const r = await api.generateReport({ subjectId, reportType, analysisMode });
      refresh();
      nav(`/reports/${r.id}`);
    } finally { setGenBusy(false); }
  }

  const subjectNameById = new Map(subjects.map((s) => [s.id, s.nickname]));
  const normalizedKeyword = keyword.trim().toLowerCase();
  const visibleReports = reports
    .filter((r) => !filterType || r.report_type === filterType)
    .filter((r) => modeFilter === 'all' || (r.analysis_mode || 'safe') === modeFilter)
    .filter((r) => {
      if (referenceFilter === 'with') return Boolean(r.has_references);
      if (referenceFilter === 'without') return !r.has_references;
      return true;
    })
    .filter((r) => {
      if (!normalizedKeyword) return true;
      const subjectName = subjectNameById.get(r.subject_id) || '';
      const text = [
        r.title,
        r.content,
        r.report_type,
        typeLabel(r.report_type),
        subjectName,
      ].filter(Boolean).join(' ').toLowerCase();
      return text.includes(normalizedKeyword);
    })
    .sort((a, b) => {
      const at = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bt = b.created_at ? new Date(b.created_at).getTime() : 0;
      return sortOrder === 'asc' ? at - bt : bt - at;
    });

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
            <Select value={reportType} onChange={setReportType} style={{ width: 170 }} options={GENERATE_TYPES} />
            <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
            <Button type="primary" disabled={!subjectId} loading={genBusy} onClick={onGenerate}>生成报告</Button>
          </Space>
        }
      />

      <PaperCard
        title="报告列表"
        extra={`显示 ${visibleReports.length} / 共 ${reports.length} 篇`}
      >
        <Space size={12} wrap style={{ marginBottom: 16 }}>
          <Select
            allowClear
            placeholder="全部类型"
            style={{ width: 170 }}
            value={filterType || undefined}
            onChange={(value) => setFilterType(value || '')}
            options={[{ value: '', label: '全部类型' }, ...TYPES]}
          />
          <Input.Search
            allowClear
            placeholder="搜索报告标题、正文关键词或命主"
            style={{ width: 260 }}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
          <Segmented
            value={modeFilter}
            onChange={setModeFilter}
            options={[
              { label: '全部模式', value: 'all' },
              { label: '普通模式', value: 'safe' },
              { label: '自用研究', value: 'research' },
            ]}
          />
          <Segmented
            value={referenceFilter}
            onChange={setReferenceFilter}
            options={[
              { label: '全部引用', value: 'all' },
              { label: '有引用', value: 'with' },
              { label: '无引用', value: 'without' },
            ]}
          />
          <Segmented
            value={sortOrder}
            onChange={setSortOrder}
            options={[
              { label: '最新优先', value: 'desc' },
              { label: '最早优先', value: 'asc' },
            ]}
          />
        </Space>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 30 }}><Spin /></div>
        ) : visibleReports.length === 0 ? (
          <Empty
            description={reports.length ? '没有找到匹配的报告，换个类型或关键词试试' : '暂无报告，选择命主后生成第一份分析报告'}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <List
            className="ml-list"
            dataSource={visibleReports}
            renderItem={(r) => (
              <List.Item
                style={{ cursor: 'pointer' }}
                onClick={() => nav(`/reports/${r.id}`)}
              >
                <List.Item.Meta
                  title={
                    <span style={{ fontFamily: 'var(--ml-font-serif)', color: 'var(--ml-text)' }}>{r.title}</span>
                  }
                  description={
                    <span style={{ color: 'var(--ml-text-faint)', fontSize: 12 }}>
                      {fmtLocal(r.created_at)} · {typeLabel(r.report_type)}
                      {subjectNameById.get(r.subject_id) ? ` · ${subjectNameById.get(r.subject_id)}` : ''}
                      {' '}
                      <Tag color={r.has_references ? 'green' : 'default'} style={{ marginLeft: 8 }}>
                        {r.has_references ? '有引用' : '无引用'}
                      </Tag>
                      <AnalysisModeTag mode={r.analysis_mode || 'safe'} />
                    </span>
                  }
                />
                <Button
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    nav(`/reports/${r.id}`);
                  }}
                >
                  查看详情
                </Button>
              </List.Item>
            )}
          />
        )}
      </PaperCard>
    </div>
  );
}
