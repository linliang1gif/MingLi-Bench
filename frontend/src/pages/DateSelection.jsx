import React, { useState } from 'react';
import { Alert, Button, Form, Input, message, Select, Space, Tag } from 'antd';
import api from '../services/api';
import AnalysisModeSelector, { AnalysisModeTag } from '../components/AnalysisModeSelector';
import PageBanner from '../components/PageBanner';
import PaperCard from '../components/PaperCard';
import MarkdownView from '../components/MarkdownView';

const TYPES = [
  { value: 'wedding', label: '婚期择日' },
  { value: 'move-in', label: '搬家入宅' },
  { value: 'opening', label: '开业择日' },
  { value: 'renovation', label: '装修开工' },
  { value: 'bed', label: '安床择日' },
];

const splitLines = (v) => String(v || '').split(/\n|,|，/).map((x) => x.trim()).filter(Boolean);

export default function DateSelection() {
  const [form] = Form.useForm();
  const [type, setType] = useState('wedding');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [analysisMode, setAnalysisMode] = useState('safe');

  async function onGenerate() {
    const values = await form.validateFields();
    setBusy(true);
    try {
      const payload = {
        ...values,
        analysisMode,
        available_dates: splitLines(values.available_dates_text),
        constraints: splitLines(values.constraints_text),
      };
      delete payload.available_dates_text;
      delete payload.constraints_text;
      setResult(await api.dateSelection(type, payload));
    } catch (e) {
      message.error(e.message || '生成失败');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageBanner title="择日黄历" subtitle="婚期、入宅、开业、装修、安床的结构化择日参考" quote="择其可行，取其安稳。" />
      <PaperCard title="择日条件" style={{ marginBottom: 18 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Select value={type} onChange={setType} options={TYPES} style={{ width: 180 }} />
          <AnalysisModeSelector value={analysisMode} onChange={setAnalysisMode} />
          <Form form={form} layout="vertical" initialValues={{
            start_date: '2026-10-01',
            end_date: '2026-10-07',
            city: '湖南怀化麻阳',
            available_dates_text: '2026-10-01\n2026-10-02\n2026-10-03',
          }}>
            <Space style={{ width: '100%' }} size={12}>
              <Form.Item name="start_date" label="开始日期" rules={[{ required: true }]} style={{ width: 160 }}><Input /></Form.Item>
              <Form.Item name="end_date" label="结束日期" rules={[{ required: true }]} style={{ width: 160 }}><Input /></Form.Item>
              <Form.Item name="city" label="城市" style={{ width: 220 }}><Input /></Form.Item>
            </Space>
            <Space style={{ width: '100%' }} size={12}>
              <Form.Item name="male_birth" label="男方生日" style={{ width: 180 }}><Input placeholder="YYYY-MM-DD" /></Form.Item>
              <Form.Item name="female_birth" label="女方生日" style={{ width: 180 }}><Input placeholder="YYYY-MM-DD" /></Form.Item>
            </Space>
            <Form.Item name="available_dates_text" label="可选日期"><Input.TextArea rows={3} /></Form.Item>
            <Form.Item name="constraints_text" label="现实约束"><Input.TextArea rows={3} placeholder="国庆期间&#10;酒店档期有限" /></Form.Item>
            <Form.Item name="notes" label="备注"><Input.TextArea rows={3} /></Form.Item>
          </Form>
          <Button type="primary" loading={busy} onClick={onGenerate}>生成择日报告</Button>
        </Space>
      </PaperCard>

      {result && (
        <PaperCard title="择日结果" extra={result.record_id ? `记录 #${result.record_id}` : undefined}>
          <Space wrap style={{ marginBottom: 12 }}>
            <AnalysisModeTag mode={result.analysis_mode || analysisMode} />
            {(result.recommended_dates || []).map((d) => <Tag color="green" key={d}>推荐 {d}</Tag>)}
            {(result.backup_dates || []).map((d) => <Tag color="blue" key={d}>备选 {d}</Tag>)}
          </Space>
          {result.risk_check_result && (result.risk_check_result.hits || []).length > 0 && (
            <Alert
              type={result.analysis_mode === 'research' ? 'info' : 'warning'}
              showIcon
              message={result.analysis_mode === 'research' ? '研究模式风险词记录' : '输出命中风险词'}
              style={{ marginBottom: 12 }}
            />
          )}
          <MarkdownView content={result.markdown} />
        </PaperCard>
      )}
    </div>
  );
}
