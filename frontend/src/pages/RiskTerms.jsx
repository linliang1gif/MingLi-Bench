import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Empty, Input, message, Select, Space, Table, Tag } from 'antd';
import api from '../services/api';
import AnalysisModeSelector, { AnalysisModeTag } from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';

const severityColor = { high: 'red', medium: 'orange', low: 'blue' };
const knownCategories = [
  '生死恐吓',
  '灾祸恐吓',
  '婚恋强断',
  '子女强断',
  '财运承诺',
  '诱导消费',
  '医疗判断',
  '宗教法事',
  '歧视侮辱',
  '绝对化承诺',
];

export default function RiskTerms() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [initBusy, setInitBusy] = useState(false);
  const [text, setText] = useState('');
  const [checkResult, setCheckResult] = useState(null);
  const [checkBusy, setCheckBusy] = useState(false);
  const [analysisMode, setAnalysisMode] = useState('safe');
  const [filters, setFilters] = useState({ category: undefined, severity: undefined });

  const categoryOptions = useMemo(
    () => Array.from(new Set([...knownCategories, ...rows.map((r) => r.category).filter(Boolean)]))
      .sort()
      .map((value) => ({ value, label: value })),
    [rows],
  );

  function refresh(nextFilters = filters) {
    setLoading(true);
    api.listRiskTerms(nextFilters)
      .then(setRows)
      .catch((e) => {
        message.error(e.message || '读取风险词失败');
        setRows([]);
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    refresh(filters);
  }, []);

  async function onInit() {
    setInitBusy(true);
    try {
      const res = await api.initRiskTerms();
      message.success(`初始化完成，新增 ${res.inserted || 0} 条，更新 ${res.updated || 0} 条`);
      refresh();
    } catch (e) {
      message.error(e.message || '初始化失败');
    } finally {
      setInitBusy(false);
    }
  }

  function updateFilter(key, value) {
    const next = { ...filters, [key]: value || undefined };
    setFilters(next);
    refresh(next);
  }

  async function onCheck() {
    setCheckBusy(true);
    try {
      setCheckResult(await api.checkRisk(text, analysisMode));
    } catch (e) {
      message.error(e.message || '审核失败');
    } finally {
      setCheckBusy(false);
    }
  }

  const columns = [
    { title: '风险词', dataIndex: 'term', width: 140, render: (v) => <b>{v}</b> },
    { title: '分类', dataIndex: 'category', width: 120 },
    {
      title: '级别',
      dataIndex: 'severity',
      width: 90,
      render: (v) => <Tag color={severityColor[v] || 'default'}>{v}</Tag>,
    },
    { title: '替代表达建议', dataIndex: 'replacement_suggestion' },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 80,
      render: (v) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>,
    },
  ];

  return (
    <div>
      <PageBanner
        title="风险词管理"
        subtitle="所有 AI 输出统一经过风险词审核"
        quote="言有所戒，辞有所守。"
        extra={
          <Space>
            <Button onClick={() => refresh()}>刷新</Button>
            <Button type="primary" loading={initBusy} onClick={onInit}>初始化风险词</Button>
          </Space>
        }
      />

      <PaperCard title="文本审核" style={{ marginBottom: 18 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Input.TextArea
            rows={4}
            placeholder="输入待审核文本"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <Space wrap>
            <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
            <Button type="primary" loading={checkBusy} onClick={onCheck} disabled={!text.trim()}>
              审核文本
            </Button>
          </Space>
          {checkResult && (
            <Alert
              type={(checkResult.hits || []).length ? (checkResult.analysis_mode === 'research' ? 'info' : 'warning') : 'success'}
              showIcon
              message={
                <Space>
                  <AnalysisModeTag mode={checkResult.analysis_mode || analysisMode} />
                  <span>{(checkResult.hits || []).length ? `命中 ${checkResult.hits?.length || 0} 个风险词` : '审核通过'}</span>
                </Space>
              }
              description={
                checkResult.hits?.length
                  ? checkResult.hits
                    .map((h) => `${h.term}（${h.category}/${h.severity}）：${h.allowed_by_research_mode ? (h.safety_note || '自用研究模式允许作为传统术语展示') : (h.replacement_suggestion || '请改为温和表达')}`)
                    .join('；')
                  : '未发现已启用风险词'
              }
            />
          )}
        </Space>
      </PaperCard>

      <PaperCard
        title="风险词列表"
        extra={
          <Space>
            <Select
              allowClear
              placeholder="按分类筛选"
              value={filters.category}
              onChange={(v) => updateFilter('category', v)}
              options={categoryOptions}
              style={{ width: 180 }}
            />
            <Select
              allowClear
              placeholder="按级别筛选"
              value={filters.severity}
              onChange={(v) => updateFilter('severity', v)}
              options={[
                { value: 'high', label: 'high' },
                { value: 'medium', label: 'medium' },
                { value: 'low', label: 'low' },
              ]}
              style={{ width: 150 }}
            />
            <span>共 {rows.length} 条</span>
          </Space>
        }
      >
        {rows.length === 0 && !loading ? (
          <Empty description="暂无风险词，点击初始化" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table
            rowKey="id"
            loading={loading}
            dataSource={rows}
            columns={columns}
            pagination={{ pageSize: 20 }}
          />
        )}
      </PaperCard>
    </div>
  );
}
