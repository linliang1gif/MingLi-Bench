import React, { useState } from 'react';
import { Alert, Button, Form, Input, InputNumber, List, message, Select, Space, Tag } from 'antd';
import api from '../services/api';
import AnalysisModeSelector, { AnalysisModeTag } from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';
import MarkdownView from '../components/MarkdownView';

const TYPES = [
  { value: 'company', label: '公司起名' },
  { value: 'brand', label: '品牌起名' },
  { value: 'shop', label: '店铺起名' },
  { value: 'baby', label: '宝宝起名' },
];

const splitWords = (v) => String(v || '').split(/,|，|\n/).map((x) => x.trim()).filter(Boolean);

export default function Naming() {
  const [form] = Form.useForm();
  const [type, setType] = useState('company');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [analysisMode, setAnalysisMode] = useState('safe');

  async function onGenerate() {
    const values = await form.validateFields();
    setBusy(true);
    try {
      const payload = {
        ...values,
        analysisMode,
        keywords: splitWords(values.keywords_text),
        avoid_words: splitWords(values.avoid_words_text),
      };
      delete payload.keywords_text;
      delete payload.avoid_words_text;
      setResult(await api.naming(type, payload));
    } catch (e) {
      message.error(e.message || '生成失败');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageBanner title="起名工具" subtitle="宝宝、公司、店铺、品牌命名候选与风险提示" quote="名以载意，字以成象。" />
      <PaperCard title="起名条件" style={{ marginBottom: 18 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Select value={type} onChange={setType} options={TYPES} style={{ width: 180 }} />
          <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
          <Form form={form} layout="vertical" initialValues={{
            industry: 'AI传统文化工具',
            style: '国风、高级、可信、科技感',
            keywords_text: '易,象,玄,知,阁',
            avoid_words_text: '神,仙,改命',
            count: 20,
          }}>
            <Space style={{ width: '100%' }} size={12}>
              <Form.Item name="industry" label="行业/方向" style={{ width: 260 }}><Input /></Form.Item>
              <Form.Item name="count" label="数量" style={{ width: 120 }}><InputNumber min={1} max={50} style={{ width: '100%' }} /></Form.Item>
            </Space>
            <Form.Item name="style" label="风格"><Input /></Form.Item>
            <Form.Item name="keywords_text" label="偏好字词"><Input.TextArea rows={2} /></Form.Item>
            <Form.Item name="avoid_words_text" label="避用字词"><Input.TextArea rows={2} /></Form.Item>
            <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
          </Form>
          <Button type="primary" loading={busy} onClick={onGenerate}>生成名字</Button>
        </Space>
      </PaperCard>

      {result && (
        <PaperCard title="起名结果" extra={result.record_id ? `记录 #${result.record_id}` : undefined}>
          <div style={{ marginBottom: 12 }}>
            <AnalysisModeTag mode={result.analysis_mode || analysisMode} />
          </div>
          {result.risk_check_result && (result.risk_check_result.hits || []).length > 0 && (
            <Alert
              type={result.analysis_mode === 'research' ? 'info' : 'warning'}
              showIcon
              message={result.analysis_mode === 'research' ? '研究模式风险词记录' : '输出命中风险词'}
              style={{ marginBottom: 12 }}
            />
          )}
          {Array.isArray(result.names) && result.names.length > 0 && (
            <List
              dataSource={result.names}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={<Space><b>{item.name}</b><Tag color="green">{item.score}</Tag></Space>}
                    description={`${item.meaning || ''} ${item.style_match || ''} ${item.risk_note || ''}`}
                  />
                </List.Item>
              )}
            />
          )}
          <MarkdownView content={result.markdown} />
        </PaperCard>
      )}
    </div>
  );
}
